import streamlit as st
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import utils
import icon_library
import tempfile
from pathlib import Path
import json
import io

st.set_page_config(page_title="Infographic Maps", layout="wide", page_icon="🎨")

st.title("🎨 Infographic Map Studio")
st.caption("Create beautiful infographic-style maps with icons, symbols, and custom styling | **Code/Author: Alfrick Onyinkwa**")

# Sidebar
with st.sidebar:
    st.header("1) Data Input")
    up = st.file_uploader("Upload GPKG / GeoJSON / Shapefile", type=["gpkg","geojson","json","zip","shp"])
    
    st.header("2) Map Style")
    style_preset = st.selectbox("Style Preset", [
        "Infographic (Icons)",
        "Minimalist Clean",
        "Bold Colors",
        "Pastel Soft",
        "Dark Theme"
    ])
    
    st.header("3) Icon Settings")
    use_icons = st.checkbox("Add Icons to Regions", value=True)
    
    if use_icons:
        icon_type = st.selectbox("Icon Type", [
            "oil", "gold", "fish", "tree", "factory", 
            "hospital", "school", "custom"
        ])
        icon_size = st.slider("Icon Size", 0.01, 0.1, 0.03)
    
    st.header("4) Labels")
    show_labels = st.checkbox("Show Region Labels", value=True)
    label_column = None

if not up:
    st.info("📤 Upload a dataset to create your infographic map.")
    
    # Show examples
    st.subheader("Example Maps You Can Create:")
    st.markdown("""
    - **Resource Maps**: Show natural resources with icons (oil, gold, minerals)
    - **Economic Maps**: Display industries and products by region
    - **Demographic Maps**: Population, education, health facilities
    - **Transportation**: Roads, airports, ports with custom symbols
    - **Environmental**: Forests, water bodies, protected areas
    """)
    st.stop()

# Load Data
tmpdir = Path(tempfile.mkdtemp(prefix='infographic_'))
file_path = tmpdir / up.name
file_path.write_bytes(up.read())

if file_path.suffix.lower() == '.gpkg':
    file_path = utils.ensure_usable_gpkg(file_path)

layers = utils.list_layers_safe(file_path)
layer = st.selectbox("Select Layer", layers) if len(layers) > 1 else layers[0]
gdf = utils.read_layer_any(file_path, layer)

# Reprojection
if gdf.crs is None:
    gdf = gdf.set_crs(4326)
else:
    gdf = gdf.to_crs(4326)

# Column selection
all_cols = [c for c in gdf.columns if c != 'geometry']
str_cols = [c for c in all_cols if pd.api.types.is_string_dtype(gdf[c])]
num_cols = utils.numeric_columns(gdf)

if show_labels and str_cols:
    label_column = st.selectbox("Label Column", str_cols)

# Color by category
category_col = st.selectbox("Color by Category", ["(None)"] + all_cols)

# Create Map
st.subheader("🗺️ Infographic Map")

fig, ax = plt.subplots(figsize=(16, 12), facecolor='white')

# Style presets
if style_preset == "Infographic (Icons)":
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE']
    edge_color = '#2C3E50'
    bg_color = '#ECF0F1'
elif style_preset == "Minimalist Clean":
    colors = ['#E8E8E8', '#D0D0D0', '#B8B8B8', '#A0A0A0', '#888888']
    edge_color = '#FFFFFF'
    bg_color = '#FFFFFF'
elif style_preset == "Bold Colors":
    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C']
    edge_color = '#2C3E50'
    bg_color = '#FFFFFF'
elif style_preset == "Pastel Soft":
    colors = ['#FFB6C1', '#B0E0E6', '#98FB98', '#FFE4B5', '#DDA0DD', '#F0E68C']
    edge_color = '#D3D3D3'
    bg_color = '#FFFAF0'
else:  # Dark Theme
    colors = ['#1F618D', '#117A65', '#7D3C98', '#B9770E', '#A93226']
    edge_color = '#ECF0F1'
    bg_color = '#2C3E50'

ax.set_facecolor(bg_color)
fig.patch.set_facecolor(bg_color)

# Assign colors
if category_col != "(None)":
    unique_cats = gdf[category_col].unique()
    color_map = {cat: colors[i % len(colors)] for i, cat in enumerate(unique_cats)}
    gdf['plot_color'] = gdf[category_col].map(color_map)
else:
    gdf['plot_color'] = colors[0]

# Plot polygons
gdf.plot(ax=ax, color=gdf['plot_color'], edgecolor=edge_color, linewidth=0.8, alpha=0.85)

# Add icons
if use_icons:
    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid
        try:
            icon_library.add_icon_to_map(ax, centroid.x, centroid.y, icon_type, 
                                        color='#2C3E50', size=icon_size)
        except:
            pass  # Skip if icon fails

# Add labels
if show_labels and label_column:
    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid
        label_text = str(row[label_column])
        icon_library.add_text_label(ax, centroid.x, centroid.y, label_text, 
                                    fontsize=8, color='#2C3E50',
                                    bbox_style='round,pad=0.3')

# Legend
if category_col != "(None)":
    legend_elements = icon_library.create_infographic_legend(
        list(color_map.keys()), 
        list(color_map.values())
    )
    ax.legend(handles=legend_elements, loc='upper left', frameon=True, 
             fancybox=True, shadow=True, fontsize=10, title=category_col)

# Title
plt.title("Infographic Map", fontsize=24, fontweight='bold', pad=20, color='#2C3E50')

# Credits
plt.figtext(0.98, 0.02, "Author: Alfrick Onyinkwa", ha='right', fontsize=10, 
           bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

ax.axis('off')
plt.tight_layout()

st.pyplot(fig)

# Export
st.subheader("📥 Export")
buf = io.BytesIO()
plt.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor=bg_color)
buf.seek(0)
st.download_button("⬇️ Download High-Res PNG", data=buf, file_name="infographic_map.png", mime="image/png")

plt.close(fig)
