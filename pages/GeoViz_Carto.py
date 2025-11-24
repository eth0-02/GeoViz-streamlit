import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import utils
import tempfile
from pathlib import Path
import matplotlib.tri as tri
import numpy as np
import json
import io

st.set_page_config(page_title="GeoViz Carto Pro", layout="wide", page_icon="🗺️")

st.title("🗺️ GeoViz Carto: Professional Cartography Studio")
st.caption("Create UN/NGO/Embassy-grade maps | **Code/Author: Alfrick Onyinkwa**")

# -----------------------------------------------------------------------------
# Sidebar: Data & Template
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("1) Data Input")
    up = st.file_uploader("Upload GPKG / GeoJSON / Shapefile", type=["gpkg","geojson","json","zip","shp"])
    
    st.header("2) Institutional Template")
    template_choice = st.selectbox("Template", [
        "UN Standard", 
        "FAO Standard", 
        "World Bank",
        "Esri Professional",
        "National Geographic",
        "New York Times",
        "The Economist",
        "Modern Minimalist",
        "Custom"
    ])
    
    # Load template
    template_map = {
        "UN Standard": "templates/un_template.json",
        "FAO Standard": "templates/fao_template.json",
        "World Bank": "templates/worldbank_template.json",
        "Esri Professional": "templates/esri_template.json",
        "National Geographic": "templates/natgeo_template.json",
        "New York Times": "templates/nyt_template.json",
        "The Economist": "templates/economist_template.json",
        "Modern Minimalist": "templates/minimalist_template.json"
    }
    
    if template_choice != "Custom":
        with open(template_map[template_choice], 'r') as f:
            template = json.load(f)
    else:
        template = {
            "colors": {"primary": "#009edb", "text": "#333333", "background": "#ffffff"},
            "elements": {"show_graticules": True, "show_disclaimer": True, 
                        "disclaimer_text": "Map for illustrative purposes only."}
        }
    
    st.header("3) Map Type & Classification")
    map_type = st.selectbox("Type", ["Choropleth", "Contours (Filled)"])
    
    if map_type == "Choropleth":
        st.caption("Classification Scheme")
        scheme_name = st.selectbox("Scheme", ["Quantiles", "Equal Interval", "Jenks", "Continuous"], index=0)
        if scheme_name != "Continuous":
            k_classes = st.slider("Classes", 3, 9, 5)
    
    st.header("4) Styling")
    cmap = st.selectbox("Colormap", [
        "YlOrRd", "RdYlGn_r", "Blues", "Greens", "Purples",
        "viridis", "plasma", "inferno", "magma", "cividis",
        "Spectral_r", "RdBu_r", "PiYG", "BrBG"
    ])
    font_name = st.selectbox("Font", ["Roboto (Sans)", "Merriweather (Serif)", "Montserrat (Modern)", "Playfair Display"])
    font_props = utils.get_font_properties(font_name)
    
    # Custom Colors
    with st.expander("🎨 Advanced Color Customization"):
        custom_primary = st.color_picker("Primary Color", template["colors"]["primary"])
        custom_text = st.color_picker("Text Color", template["colors"]["text"])
        template["colors"]["primary"] = custom_primary
        template["colors"]["text"] = custom_text
    
    use_basemap = st.checkbox("Add Basemap", value=False)
    if use_basemap:
        basemap_source = st.selectbox("Provider", ["CartoDB.Positron", "CartoDB.Voyager", "Esri.WorldGrayCanvas", "Esri.WorldImagery"])
        alpha = st.slider("Layer Opacity", 0.0, 1.0, 0.8)
    else:
        alpha = 1.0
    
    st.header("5) Professional Elements")
    show_graticules = st.checkbox("Graticules (Lat/Long Grid)", value=template["elements"]["show_graticules"])
    show_inset = st.checkbox("Inset Locator Map", value=template["elements"].get("show_inset", False))
    show_north = st.checkbox("North Arrow", value=True)
    north_style = st.selectbox("Arrow Style", ["Simple", "Fancy", "Minimal"])
    show_scale = st.checkbox("Scale Bar", value=True)
    
    # Logo Upload
    logo_file = st.file_uploader("📷 Upload Organization Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])
    
    st.header("6) Layout")
    page_size = st.selectbox("Page Size", ["A4", "A3", "Letter"])
    orientation = st.selectbox("Orientation", ["Portrait", "Landscape"])
    
    title = st.text_input("Map Title", "GEOSPATIAL ANALYSIS")
    subtitle = st.text_input("Subtitle", f"Created with GeoViz Studio | {template_choice}")
    
    st.header("7) Export Format")
    export_format = st.selectbox("Format", ["High-Res PNG (300 DPI)", "Vector PDF", "SVG (Illustrator)"])

if not up:
    st.info("📤 Upload a dataset to begin creating your professional map.")
    st.stop()

# Load Data
tmpdir = Path(tempfile.mkdtemp(prefix='carto_'))
file_path = tmpdir / up.name
file_path.write_bytes(up.read())

if file_path.suffix.lower() == '.gpkg':
    file_path = utils.ensure_usable_gpkg(file_path)

layers = utils.list_layers_safe(file_path)
layer = st.selectbox("Select Layer", layers) if len(layers) > 1 else layers[0]
gdf = utils.read_layer_any(file_path, layer)

# Reprojection
target_crs = 3857 if use_basemap else 4326
if gdf.crs is None:
    gdf = gdf.set_crs(target_crs)
else:
    gdf = gdf.to_crs(target_crs)

num_cols = utils.numeric_columns(gdf)
if not num_cols:
    st.error("No numeric columns found.")
    st.stop()

col = st.selectbox("Column to Visualize", num_cols)

# Analysis Section
st.subheader("📊 Data Analysis & Notes")
col1, col2 = st.columns(2)
with col1:
    if st.button("📊 Generate Statistics"):
        analysis_text = utils.analyze_data(gdf, col)
        st.session_state['analysis'] = analysis_text

with col2:
    if st.button("🤖 AI Insights (Gemini)"):
        api_key = "AIzaSyB9N7PB-VEbALC2EcnXQdY_B50QRTpcBL0"
        with st.spinner("AI analyzing..."):
            ai_text = utils.generate_ai_insights(gdf, col, api_key)
            st.session_state['ai_insights'] = ai_text

notes_default = st.session_state.get('analysis', '') + "\n\n" + st.session_state.get('ai_insights', '')
map_notes = st.text_area("Map Notes", notes_default if notes_default.strip() else "Data Source: ...", height=100)

disclaimer_text = st.text_area("Disclaimer", template["elements"]["disclaimer_text"], height=80)

# -----------------------------------------------------------------------------
# PROFESSIONAL MAP RENDERING
# -----------------------------------------------------------------------------
st.subheader("🗺️ Map Preview")

# Page size configuration
page_sizes = {
    "A4": (8.27, 11.69) if orientation == "Portrait" else (11.69, 8.27),
    "A3": (11.69, 16.54) if orientation == "Portrait" else (16.54, 11.69),
    "Letter": (8.5, 11) if orientation == "Portrait" else (11, 8.5)
}
figsize = page_sizes[page_size]

# Create figure with professional layout
fig = plt.figure(figsize=figsize, facecolor='white')

# Define layout grid
# Header: 10%, Map: 70%, Legend/Footer: 15%, Disclaimer: 5%
gs = fig.add_gridspec(4, 1, height_ratios=[0.10, 0.70, 0.15, 0.05], hspace=0.02)

# Header
ax_header = fig.add_subplot(gs[0, 0])
ax_header.axis('off')
ax_header.text(0.5, 0.6, title, ha='center', va='center', fontsize=20, fontweight='bold', 
               color=template["colors"]["primary"], **font_props)
ax_header.text(0.5, 0.2, subtitle, ha='center', va='center', fontsize=11, 
               color=template["colors"]["text"], **font_props)

# Main Map
ax_map = fig.add_subplot(gs[1, 0])

# Plot data
if map_type == "Choropleth":
    if scheme_name == "Continuous":
        gdf.plot(column=col, ax=ax_map, cmap=cmap, legend=False, alpha=alpha,
                 edgecolor='#666666', linewidth=0.3)
    else:
        scheme_map = {"Quantiles": "quantiles", "Equal Interval": "equal_interval", "Jenks": "fisher_jenks"}
        scheme = scheme_map.get(scheme_name, "quantiles")
        gdf.plot(column=col, ax=ax_map, cmap=cmap, legend=False, scheme=scheme, k=k_classes, alpha=alpha,
                 edgecolor='#666666', linewidth=0.3)

elif map_type == "Contours (Filled)":
    from scipy.interpolate import griddata
    points = gdf.geometry.centroid
    x, y, z = points.x, points.y, gdf[col].fillna(0)
    xi = np.linspace(x.min(), x.max(), 200)
    yi = np.linspace(y.min(), y.max(), 200)
    xi, yi = np.meshgrid(xi, yi)
    zi = griddata((x, y), z, (xi, yi), method='cubic')
    ax_map.contourf(xi, yi, zi, levels=14, cmap=cmap, alpha=alpha)
    gdf.plot(ax=ax_map, facecolor='none', edgecolor='#555555', linewidth=0.2)

# Basemap
if use_basemap:
    import contextily as ctx
    provider = ctx.providers.CartoDB.Positron
    if basemap_source == "CartoDB.Voyager": provider = ctx.providers.CartoDB.Voyager
    if basemap_source == "Esri.WorldGrayCanvas": provider = ctx.providers.Esri.WorldGrayCanvas
    try:
        ctx.add_basemap(ax_map, crs=gdf.crs.to_string(), source=provider, alpha=0.5)
    except: pass

# Graticules
if show_graticules:
    ax_map.grid(True, linestyle=':', alpha=0.4, color='#666666', linewidth=0.5)
    ax_map.tick_params(labelsize=7)

# North Arrow
if show_north:
    utils.draw_north_arrow(ax_map, location=(0.95, 0.92), size=0.04, style=north_style)

# Scale Bar
if show_scale:
    utils.draw_scale_bar(ax_map, gdf.total_bounds, crs_is_geographic=(target_crs == 4326))

ax_map.set_xlabel("Longitude" if target_crs == 4326 else "Easting (m)", fontsize=8)
ax_map.set_ylabel("Latitude" if target_crs == 4326 else "Northing (m)", fontsize=8)

# Footer (Legend + Credits + Logo)
ax_footer = fig.add_subplot(gs[2, 0])
ax_footer.axis('off')

# Create legend manually
s = pd.to_numeric(gdf[col], errors='coerce')
if scheme_name != "Continuous" and map_type == "Choropleth":
    from mapclassify import classify
    bins = classify(s, scheme=scheme, k=k_classes)
    cmap_obj = plt.cm.get_cmap(cmap, k_classes)
    
    legend_elements = []
    for i in range(k_classes):
        color = cmap_obj(i)
        label = f"{bins.bins[i-1]:.1f} - {bins.bins[i]:.1f}" if i > 0 else f"< {bins.bins[i]:.1f}"
        legend_elements.append(mpatches.Patch(facecolor=color, edgecolor='black', label=label))
    
    ax_footer.legend(handles=legend_elements, loc='upper left', ncol=min(k_classes, 5), 
                     frameon=True, fontsize=8, title=col)

# Logo
if logo_file is not None:
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    from PIL import Image
    logo_img = Image.open(logo_file)
    imagebox = OffsetImage(logo_img, zoom=0.08)
    ab = AnnotationBbox(imagebox, (0.5, 0.5), xycoords='axes fraction', frameon=False)
    ax_footer.add_artist(ab)

# Credits
ax_footer.text(0.98, 0.5, f"Author: Alfrick Onyinkwa | {pd.Timestamp.now().strftime('%B %Y')}", 
               ha='right', va='center', fontsize=9, **font_props)

# Disclaimer
ax_disclaimer = fig.add_subplot(gs[3, 0])
ax_disclaimer.axis('off')
ax_disclaimer.text(0.5, 0.5, disclaimer_text, ha='center', va='center', fontsize=7, 
                   color='#666666', style='italic', wrap=True, **font_props)

plt.tight_layout()

# Display
st.pyplot(fig)

# Export
st.subheader("📥 Export Your Map")

if export_format == "High-Res PNG (300 DPI)":
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    st.download_button("⬇️ Download PNG", data=buf, file_name="professional_map.png", mime="image/png")

elif export_format == "Vector PDF":
    pdf_buf = io.BytesIO()
    with PdfPages(pdf_buf) as pdf:
        pdf.savefig(fig, bbox_inches='tight')
    pdf_buf.seek(0)
    st.download_button("⬇️ Download PDF", data=pdf_buf, file_name="professional_map.pdf", mime="application/pdf")

elif export_format == "SVG (Illustrator)":
    svg_buf = io.BytesIO()
    plt.savefig(svg_buf, format='svg', bbox_inches='tight')
    svg_buf.seek(0)
    st.download_button("⬇️ Download SVG", data=svg_buf, file_name="professional_map.svg", mime="image/svg+xml")

plt.close(fig)
