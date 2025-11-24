import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import utils
import tempfile
from pathlib import Path
import matplotlib.tri as tri
import numpy as np

st.set_page_config(page_title="GeoViz Carto", layout="wide")

st.title("GeoViz Carto: Professional Static Maps")
st.caption("Create high-quality, print-ready maps with contours, north arrows, and scale bars. **Code/Author: Alfrick Onyinkwa**")

# -----------------------------------------------------------------------------
# 1. Data Input
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("1) Data")
    up = st.file_uploader("Upload GPKG / GeoJSON / Shapefile", type=["gpkg","geojson","json","zip","shp"])
    
    st.header("2) Map Type")
    map_type = st.selectbox("Type", ["Choropleth", "Contours (Filled)"])
    
    # Classification (Only for Choropleth)
    if map_type == "Choropleth":
        st.caption("Classification Scheme")
        scheme_name = st.selectbox("Scheme", ["Quantiles", "Equal Interval", "Jenks", "Continuous"], index=0)
        if scheme_name != "Continuous":
            k_classes = st.slider("Classes", 3, 9, 5)
    
    st.header("3) Styling & Basemap")
    cmap = st.selectbox("Colormap", ["viridis", "plasma", "inferno", "magma", "cividis", "RdBu_r", "Spectral_r"])
    
    # Font Selection
    font_name = st.selectbox("Font Family", ["Default", "Roboto (Sans)", "Open Sans", "Montserrat (Modern)", "Merriweather (Serif)", "Playfair Display", "Monospace (Code)"])
    font_props = utils.get_font_properties(font_name)
    
    # Basemap Options
    use_basemap = st.checkbox("Add Basemap (Contextily)", value=False)
    if use_basemap:
        basemap_source = st.selectbox("Provider", ["OpenStreetMap.Mapnik", "CartoDB.Positron", "CartoDB.DarkMatter", "Esri.WorldImagery"])
        alpha = st.slider("Layer Opacity", 0.0, 1.0, 0.7)
    else:
        bg_color = st.color_picker("Background Color", "#ffffff")
        alpha = 1.0

    st.header("4) Elements")
    show_north = st.checkbox("North Arrow", value=True)
    if show_north:
        north_style = st.selectbox("Arrow Style", ["Simple", "Fancy", "Minimal"])
    
    show_scale = st.checkbox("Scale Bar", value=True)
    show_grid = st.checkbox("Gridlines", value=False)
    
    st.header("5) Layout & Legend")
    title = st.text_input("Map Title", "My Professional Map")
    subtitle = st.text_input("Subtitle", "Created with GeoViz Studio")
    
    # Legend options
    if map_type == "Choropleth" and scheme_name != "Continuous":
        legend_loc = st.selectbox("Legend Position", ["best", "lower right", "lower left", "upper right", "upper left", "center right", "outside bottom", "outside right"])
        legend_cols = st.slider("Legend Columns", 1, 4, 1)
        legend_frame = st.checkbox("Frame Legend", value=True)
    else:
        st.caption("Legend positioning is only available for classified (discrete) maps.")
    
    st.header("6) Notes & Analysis")
    default_notes = "Data source: ...\nCoordinate System: Web Mercator (EPSG:3857)"
    
    # Smart Analysis Button
    if st.button("Generate Smart Analysis"):
        analysis_text = utils.analyze_data(gdf, col)
        default_notes = analysis_text + "\n" + default_notes
        
    map_notes = st.text_area("Map Notes", default_notes, height=150)
    
    st.divider()
    st.markdown("**Code/Author:** Alfrick Onyinkwa")

if not up:
    st.info("Please upload a dataset to start.")
    st.stop()

# Load Data
tmpdir = Path(tempfile.mkdtemp(prefix='carto_'))
file_path = tmpdir / up.name
file_path.write_bytes(up.read())

if file_path.suffix.lower() == '.gpkg':
    file_path = utils.ensure_usable_gpkg(file_path)

layers = utils.list_layers_safe(file_path)
layer = st.sidebar.selectbox("Layer", layers)
gdf = utils.read_layer_any(file_path, layer)

# Reprojection Logic
target_crs = 3857 if use_basemap else 4326
if gdf.crs is None:
    st.warning(f"CRS is missing. Assuming EPSG:{target_crs}.")
    gdf = gdf.set_crs(target_crs)
else:
    gdf = gdf.to_crs(target_crs)

num_cols = utils.numeric_columns(gdf)
if not num_cols:
    st.error("No numeric columns found.")
    st.stop()

col = st.sidebar.selectbox("Column to Map", num_cols)

# -----------------------------------------------------------------------------
# 2. Rendering Engine
# -----------------------------------------------------------------------------
st.subheader("Map Preview")

fig, ax = plt.subplots(figsize=(12, 10))
if not use_basemap:
    ax.set_facecolor(bg_color)
    fig.patch.set_facecolor(bg_color)

# Plot Data
if map_type == "Choropleth":
    if scheme_name == "Continuous":
        # Continuous Colorbar
        gdf.plot(column=col, ax=ax, cmap=cmap, legend=True, alpha=alpha,
                 legend_kwds={'shrink': 0.5, 'label': col},
                 edgecolor='#333333', linewidth=0.5)
    else:
        # Discrete Legend
        scheme_map = {"Quantiles": "quantiles", "Equal Interval": "equal_interval", "Jenks": "fisher_jenks"}
        scheme = scheme_map.get(scheme_name, "quantiles")
        
        leg_kwds = {'ncol': legend_cols, 'fmt': '{:.0f}', 'frameon': legend_frame}
        
        if legend_loc == "outside bottom":
            leg_kwds.update({'loc': 'upper center', 'bbox_to_anchor': (0.5, -0.05)})
        elif legend_loc == "outside right":
            leg_kwds.update({'loc': 'center left', 'bbox_to_anchor': (1, 0.5)})
        else:
            leg_kwds.update({'loc': legend_loc})
        
        # Apply font props to legend?
        # geopandas plot doesn't easily accept fontprops for legend, but we can try to access it later
        # For now, we rely on global or post-hoc adjustment if needed, but let's just stick to standard
        
        gdf.plot(column=col, ax=ax, cmap=cmap, legend=True, scheme=scheme, k=k_classes, alpha=alpha,
                 legend_kwds=leg_kwds,
                 edgecolor='#333333', linewidth=0.5)

elif map_type == "Contours (Filled)":
    # Generate contours from centroids
    points = gdf.geometry.centroid
    x = points.x
    y = points.y
    z = gdf[col].fillna(0)
    
    # Interpolation / Smoothing
    from scipy.interpolate import griddata
    
    # Create a grid
    xi = np.linspace(x.min(), x.max(), 200)
    yi = np.linspace(y.min(), y.max(), 200)
    xi, yi = np.meshgrid(xi, yi)
    
    # Interpolate
    zi = griddata((x, y), z, (xi, yi), method='cubic')
    
    # Contourf on grid
    cntr = ax.contourf(xi, yi, zi, levels=14, cmap=cmap, alpha=alpha)
    
    cbar = fig.colorbar(cntr, ax=ax, shrink=0.5, label=col, pad=0.02)
    cbar.ax.tick_params(labelsize=8)
    
    gdf.plot(ax=ax, facecolor='none', edgecolor='#555555', linewidth=0.3, alpha=0.5)

# Basemap
if use_basemap:
    import contextily as ctx
    try:
        provider = ctx.providers.OpenStreetMap.Mapnik
        if basemap_source == "CartoDB.Positron": provider = ctx.providers.CartoDB.Positron
        if basemap_source == "CartoDB.DarkMatter": provider = ctx.providers.CartoDB.DarkMatter
        if basemap_source == "Esri.WorldImagery": provider = ctx.providers.Esri.WorldImagery
        
        ctx.add_basemap(ax, crs=gdf.crs.to_string(), source=provider)
    except Exception as e:
        st.error(f"Error loading basemap: {e}")

# Elements
if show_north:
    utils.draw_north_arrow(ax, style=north_style)

if show_scale:
    utils.draw_scale_bar(ax, gdf.total_bounds, crs_is_geographic=(target_crs == 4326))

if show_grid:
    ax.grid(True, linestyle='--', alpha=0.5, color='#aaaaaa')

# Layout
# Title Block
plt.figtext(0.5, 0.95, title, ha='center', fontsize=22, fontweight='bold', **font_props)
plt.figtext(0.5, 0.91, subtitle, ha='center', fontsize=14, color='#555555', **font_props)

# Map Notes (Bottom Left)
if map_notes:
    plt.figtext(0.02, 0.02, map_notes, ha='left', va='bottom', fontsize=9, color='#444444', 
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'), **font_props)

# Author Credit (Bottom Right - Prominent)
plt.figtext(0.98, 0.02, "Code/Author: Alfrick Onyinkwa", ha='right', va='bottom', 
            fontsize=11, fontweight='bold', color='#333333',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'), **font_props)

# Remove axes ticks if desired, or keep them for reference
if target_crs == 3857:
    ax.set_axis_off() # Usually cleaner for basemaps
else:
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

st.pyplot(fig)

# Export
import io
buf = io.BytesIO()
plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
buf.seek(0)

st.download_button("Download High-Res Map (PNG)", data=buf, file_name="carto_map.png", mime="image/png")
