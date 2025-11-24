import os
import tempfile
import zipfile
import subprocess
from pathlib import Path
import geopandas as gpd
import pandas as pd
import fiona
import mapclassify as mc
from matplotlib import cm, colors as mplcolors
import sqlite3
import streamlit as st

try:
    import pyogrio
    HAS_PYOGRIO = True
except Exception:
    HAS_PYOGRIO = False

def is_zip_shapefile(path: Path) -> bool:
    return path.suffix.lower() == ".zip"

def unpack_shapefile_zip(path: Path) -> Path:
    tmpdir = Path(tempfile.mkdtemp(prefix="shpzip_"))
    with zipfile.ZipFile(path, 'r') as z:
        z.extractall(tmpdir)
    shp = next(tmpdir.rglob("*.shp"), None)
    if not shp:
        raise RuntimeError("ZIP does not contain a .shp file.")
    return shp

@st.cache_data(show_spinner=False)
def list_layers_safe(path: Path):
    try:
        return fiona.listlayers(path.as_posix())
    except Exception:
        if HAS_PYOGRIO:
            try:
                return [lyr.name for lyr in pyogrio.list_layers(path.as_posix())]
            except Exception:
                pass
        return ["_single_"]

@st.cache_data(show_spinner="Loading data...")
def read_layer_any(path: Path, layer: str):
    if is_zip_shapefile(path):
        shp = unpack_shapefile_zip(path)
        return gpd.read_file(shp.as_posix())
    if HAS_PYOGRIO and layer != "_single_":
        try:
            return pyogrio.read_dataframe(path.as_posix(), layer=layer)
        except Exception:
            pass
    if HAS_PYOGRIO and layer == "_single_":
        try:
            return pyogrio.read_dataframe(path.as_posix())
        except Exception:
            pass
    if layer == "_single_":
        return gpd.read_file(path.as_posix())
    else:
        return gpd.read_file(path.as_posix(), layer=layer)

def numeric_columns(gdf: gpd.GeoDataFrame):
    return [c for c in gdf.columns if c != "geometry" and pd.api.types.is_numeric_dtype(gdf[c])]

@st.cache_data(show_spinner=False)
def classify(_values: pd.Series, scheme: str, k: int):
    """Classify values using mapclassify. Note: _values prefix for hash_funcs compatibility."""
    scheme = (scheme or "quantile").lower()
    if scheme in ["quantile","quantiles","q"]:
        return mc.Quantiles(_values, k=k)
    if scheme in ["equal","equalinterval","ei"]:
        return mc.EqualInterval(_values, k=k)
    if scheme in ["jenks","naturalbreaks","nb"]:
        return mc.NaturalBreaks(_values, k=k)
    return mc.Quantiles(_values, k=k)

@st.cache_data(show_spinner=False)
def get_cmap_hexlist(name: str, steps: int, reverse: bool=False):
    """Get color palette as hex list. Cached for performance."""
    cmap = cm.get_cmap(name, steps)
    seq = range(steps-1, -1, -1) if reverse else range(steps)
    return [mplcolors.to_hex(cmap(i)) for i in seq]

def make_continuous_legend_html(colors, vmin, vmax, label):
    grad = ",".join(colors)
    fmt = lambda x: f"{x:.1f}".rstrip('0').rstrip('.') if abs(x) < 1000 else f"{x:.0f}"
    html = f"""
    <div style='background: rgba(255,255,255,.95); border:1px solid #e5e7eb;
      border-radius:12px; padding:10px 12px; min-width:260px;
      box-shadow: 0 6px 20px rgba(15, 23, 42, .08);
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;'>
      <div style='font-size:12px; color:#0f172a; margin-bottom:6px;'>{label}</div>
      <div style='height:10px; width:100%; border-radius:6px;
                  background: linear-gradient(to right, {grad});
                  border:1px solid #e5e7eb; margin-bottom:6px;'></div>
      <div style='display:flex; justify-content:space-between; font-size:11px; color:#334155;'>
        <span>{fmt(vmin)}</span><span>{fmt(vmax)}</span>
      </div>
    </div>"""
    return html

def attempt_sqlite_vacuum(src: Path) -> Path | None:
    try:
        dst = src.with_name(src.stem + "_vacuum.gpkg")
        conn = sqlite3.connect(src.as_posix())
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check;")
        _ = cur.fetchone()
        cur.execute(f"VACUUM INTO '{dst.as_posix()}'")
        conn.close()
        return dst if dst.exists() and dst.stat().st_size > 0 else None
    except Exception:
        return None

def attempt_pyogrio_rewrite(src: Path) -> Path | None:
    if not HAS_PYOGRIO: return None
    try:
        layers = [lyr.name for lyr in pyogrio.list_layers(src.as_posix())]
        if not layers: return None
        dst = src.with_name(src.stem + '_pyogriofix.gpkg')
        for i, lyr in enumerate(layers):
            df = pyogrio.read_dataframe(src.as_posix(), layer=lyr)
            if i == 0:
                df.to_file(dst.as_posix(), layer=lyr, driver='GPKG')
            else:
                df.to_file(dst.as_posix(), layer=lyr, driver='GPKG', mode='a')
        return dst
    except Exception:
        return None

def ogr2ogr_available() -> bool:
    try:
        subprocess.run(['ogr2ogr', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return True
    except Exception:
        return False

def attempt_ogr2ogr_copy(src: Path) -> Path | None:
    if not ogr2ogr_available(): return None
    try:
        dst = src.with_name(src.stem + '_fixed.gpkg')
        subprocess.run(['ogr2ogr', '-f', 'GPKG', dst.as_posix(), src.as_posix()], check=True)
        return dst if dst.exists() and dst.stat().st_size > 0 else None
    except Exception:
        return None

def ensure_usable_gpkg(src: Path) -> Path:
    try:
        _ = fiona.listlayers(src.as_posix())
        return src
    except Exception as e:
        msg = str(e).lower()
        if 'malformed' in msg or 'disk image' in msg:
            for fixer in (attempt_sqlite_vacuum, attempt_pyogrio_rewrite, attempt_ogr2ogr_copy):
                fixed = fixer(src)
                if fixed:
                    try:
                        _ = fiona.listlayers(fixed.as_posix())
                        return fixed
                    except Exception:
                        continue
        return src

def export_geojson(df: gpd.GeoDataFrame):
    if df.crs is not None:
        df = df.to_crs(4326)
    return df.to_json()

def generate_static_map(gdf, column, colors, title, subtitle, source, logo=None):
    import matplotlib.pyplot as plt
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    import io

    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    ax.axis('off')
    
    gdf.plot(column=column, ax=ax, color=gdf['__color__'], edgecolor='#333333', linewidth=0.5)
    
    # Title & Subtitle
    plt.figtext(0.05, 0.92, title, fontsize=24, fontweight='bold', fontfamily='sans-serif')
    if subtitle:
        plt.figtext(0.05, 0.88, subtitle, fontsize=14, color='#555555', fontfamily='sans-serif')
    
    # Source
    if source:
        plt.figtext(0.05, 0.05, source, fontsize=10, color='#777777', fontfamily='sans-serif')

    # Permanent Author Credit
    plt.figtext(0.95, 0.02, "Author: Alfrick Onyinkwa", fontsize=10, color='#999999', ha='right', fontfamily='sans-serif')

    # Logo
    if logo is not None:
        image = plt.imread(logo)
        imagebox = OffsetImage(image, zoom=0.15) # Adjust zoom as needed
        ab = AnnotationBbox(imagebox, (0.9, 0.05), xycoords='axes fraction', frameon=False)
        ax.add_artist(ab)
    
    # Legend (Custom construction)
    # This is a simplified legend for the static map
    import matplotlib.patches as mpatches
    patches = []
    # We need to reconstruct the class breaks/colors mapping
    # Since we passed colors directly in gdf['__color__'], we can try to infer unique colors
    # But for a proper legend we need the ranges. 
    # For now, let's just skip the legend or make a simple gradient bar if possible.
    # A full legend reconstruction requires passing the classifier object.
    # Let's keep it simple for now.

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf

def draw_north_arrow(ax, location=(0.95, 0.95), size=0.05, style="Simple"):
    """
    Draws a north arrow on the map with different styles.
    location: (x, y) in axes coordinates.
    style: 'Simple', 'Fancy', 'Minimal'
    """
    x, y = location
    
    if style == "Simple":
        ax.text(x, y + size, "N", ha='center', va='bottom', transform=ax.transAxes, 
                fontsize=12, fontweight='bold', fontfamily='sans-serif')
        ax.annotate('', xy=(x, y + size), xytext=(x, y),
                    arrowprops=dict(facecolor='black', width=3, headwidth=10, headlength=10),
                    xycoords='axes fraction')
                    
    elif style == "Fancy":
        # A more decorative arrow
        ax.text(x, y + size + 0.02, "N", ha='center', va='bottom', transform=ax.transAxes,
                fontsize=14, fontfamily='serif', fontweight='bold')
        ax.annotate('', xy=(x, y + size), xytext=(x, y),
                    arrowprops=dict(facecolor='black', width=4, headwidth=12, headlength=12, connectionstyle="arc3,rad=.2"),
                    xycoords='axes fraction')
                    
    elif style == "Minimal":
        # Just a thin line and N
        ax.text(x, y + size + 0.01, "N", ha='center', va='bottom', transform=ax.transAxes,
                fontsize=10, fontfamily='sans-serif')
        ax.plot([x, x], [y, y + size], transform=ax.transAxes, color='black', linewidth=1.5)
        # Add a little crossbar
        ax.plot([x - size/4, x + size/4], [y + size/4, y + size/4], transform=ax.transAxes, color='black', linewidth=1)

def draw_scale_bar(ax, bounds, crs_is_geographic=True):
    """
    Draws a simple scale bar.
    bounds: (minx, miny, maxx, maxy).
    crs_is_geographic: True if bounds are in degrees, False if in meters.
    """
    import numpy as np
    minx, miny, maxx, maxy = bounds
    
    if crs_is_geographic:
        # Estimate width in km at the center latitude
        center_lat = np.radians((miny + maxy) / 2)
        deg_lat_km = 111.32
        deg_lon_km = 111.32 * np.cos(center_lat)
        
        map_width_deg = maxx - minx
        map_width_km = map_width_deg * deg_lon_km
        
        # Target ~20% of map width
        target_km = map_width_km * 0.2
        
        def round_to_nice(x):
            pow10 = 10 ** int(np.floor(np.log10(x)))
            d = x / pow10
            if d < 2: return 1 * pow10
            if d < 5: return 2 * pow10
            return 5 * pow10
        
        scale_km = round_to_nice(target_km)
        scale_deg = scale_km / deg_lon_km
        
        # Position: Bottom Left
        x0, y0 = minx + (maxx - minx) * 0.05, miny + (maxy - miny) * 0.05
        
        # Draw line
        ax.plot([x0, x0 + scale_deg], [y0, y0], color='black', linewidth=2, solid_capstyle='butt')
        
        # Ticks
        ax.plot([x0, x0], [y0, y0 + (maxy-miny)*0.01], color='black', linewidth=2)
        ax.plot([x0 + scale_deg, x0 + scale_deg], [y0, y0 + (maxy-miny)*0.01], color='black', linewidth=2)
        
        # Label
        ax.text(x0 + scale_deg/2, y0 + (maxy-miny)*0.015, f"{int(scale_km)} km", 
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    else:
        # Bounds are in meters (Web Mercator)
        map_width_m = maxx - minx
        target_m = map_width_m * 0.2
        
        def round_to_nice(x):
            pow10 = 10 ** int(np.floor(np.log10(x)))
            d = x / pow10
            if d < 2: return 1 * pow10
            if d < 5: return 2 * pow10
            return 5 * pow10
        
        scale_m = round_to_nice(target_m)
        scale_km = scale_m / 1000.0
        
        # Position: Bottom Left
        x0, y0 = minx + (maxx - minx) * 0.05, miny + (maxy - miny) * 0.05
        
        # Draw line
        ax.plot([x0, x0 + scale_m], [y0, y0], color='black', linewidth=2, solid_capstyle='butt')
        
        # Ticks
        ax.plot([x0, x0], [y0, y0 + (maxy-miny)*0.01], color='black', linewidth=2)
        ax.plot([x0 + scale_m, x0 + scale_m], [y0, y0 + (maxy-miny)*0.01], color='black', linewidth=2)
        
        # Label
        label = f"{int(scale_km)} km" if scale_km >= 1 else f"{int(scale_m)} m"
        ax.text(x0 + scale_m/2, y0 + (maxy-miny)*0.015, label, 
                ha='center', va='bottom', fontsize=10, fontweight='bold')

def analyze_data(df, col):
    """
    Generates a summary string for the given column in the dataframe.
    """
    import pandas as pd
    s = pd.to_numeric(df[col], errors='coerce').dropna()
    if s.empty:
        return "No numeric data found."
    
    desc = s.describe()
    mean_val = desc['mean']
    median_val = desc['50%']
    max_val = desc['max']
    min_val = desc['min']
    std_val = desc['std']
    
    # skewness
    skew = s.skew()
    dist_type = "normally distributed" if abs(skew) < 0.5 else ("right-skewed" if skew > 0 else "left-skewed")
    
    summary = (
        f"Analysis of '{col}':\n"
        f"- Range: {min_val:.2f} to {max_val:.2f}\n"
        f"- Average: {mean_val:.2f} (Median: {median_val:.2f})\n"
        f"- Std Dev: {std_val:.2f}\n"
        f"- Distribution: Data appears {dist_type} (skew: {skew:.2f}).\n"
    )
    return summary

def get_font_properties(font_name):
    """
    Returns a dict of font properties for matplotlib.
    """
    # Map friendly names to actual font families available in most systems or generic families
    font_map = {
        "Default": "sans-serif",
        "Roboto (Sans)": "sans-serif", # Matplotlib defaults to DejaVu Sans which is close enough or Arial
        "Merriweather (Serif)": "serif", # Matplotlib defaults to DejaVu Serif
        "Montserrat (Modern)": "sans-serif",
        "Open Sans": "sans-serif",
        "Playfair Display": "serif",
        "Monospace (Code)": "monospace"
    }
    
    family = font_map.get(font_name, "sans-serif")
    
    # If we really wanted specific Google Fonts, we'd need to download .ttf files and use font_manager.FontProperties(fname=...)
    # For now, we stick to generic families but "pretend" by setting the family preference order if possible
    # But simpler is just returning the generic family.
    
    if "Serif" in font_name or "Playfair" in font_name:
        return {'fontfamily': 'serif'}
    elif "Monospace" in font_name:
        return {'fontfamily': 'monospace'}
    else:
        return {'fontfamily': 'sans-serif'}

def generate_ai_insights(df, col, api_key):
    """
    Uses Google Gemini API to generate intelligent insights about the data.
    """
    try:
        import google.generativeai as genai
        
        # Get basic stats
        s = pd.to_numeric(df[col], errors='coerce').dropna()
        if s.empty:
            return "No numeric data available for AI analysis."
        
        desc = s.describe()
        
        # Prepare context for AI
        context = f"""
        Dataset Analysis Request:
        - Column: {col}
        - Total Records: {len(df)}
        - Mean: {desc['mean']:.2f}
        - Median: {desc['50%']:.2f}
        - Min: {desc['min']:.2f}
        - Max: {desc['max']:.2f}
        - Std Dev: {desc['std']:.2f}
        - Skewness: {s.skew():.2f}
        
        Generate a concise, professional 2-3 sentence narrative describing:
        1. The overall pattern/distribution
        2. Any notable insights or anomalies
        3. What this might indicate for decision-makers
        
        Keep it under 100 words and use clear, non-technical language.
        """
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        response = model.generate_content(context)
        
        insight = response.text.strip()
        return f"🤖 AI Insights (Gemini):\n{insight}"
        
    except Exception as e:
        return f"AI Analysis unavailable: {str(e)}"



