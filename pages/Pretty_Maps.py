import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox
import tempfile
from pathlib import Path
import utils
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import io

st.set_page_config(page_title="Pretty Maps Pro", layout="wide", page_icon="🎨")

st.title("🎨 Pretty Maps Pro - Artistic Cartography Studio")
st.caption("Professional artistic map generation | **Code/Author: Alfrick Onyinkwa**")

# Sidebar
with st.sidebar:
    st.header("📍 Location Input")
    
    input_method = st.radio("Input Method", ["Address/Place", "Coordinates", "Bounding Box", "Upload GeoJSON"])
    
    if input_method == "Address/Place":
        location = st.text_input("Enter Location", "Central Park, New York City")
        radius = st.slider("Radius (meters)", 100, 5000, 800, 100)
        
    elif input_method == "Coordinates":
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", value=40.7829, format="%.6f")
        with col2:
            lon = st.number_input("Longitude", value=-73.9654, format="%.6f")
        radius = st.slider("Radius (meters)", 100, 5000, 800, 100)
        location = (lat, lon)
        
    elif input_method == "Bounding Box":
        st.caption("Define custom bounding box")
        col1, col2 = st.columns(2)
        with col1:
            north = st.number_input("North", value=40.80, format="%.6f")
            south = st.number_input("South", value=40.76, format="%.6f")
        with col2:
            east = st.number_input("East", value=-73.95, format="%.6f")
            west = st.number_input("West", value=-73.99, format="%.6f")
        bbox = (north, south, east, west)
        location = None
        
    else:  # Upload GeoJSON
        up = st.file_uploader("Upload GeoJSON/GPKG", type=["geojson", "json", "gpkg"])
        if not up:
            st.info("📤 Upload a GeoJSON or GPKG file")
            st.stop()
        else:
            tmpdir = Path(tempfile.mkdtemp(prefix='prettymap_'))
            file_path = tmpdir / up.name
            file_path.write_bytes(up.read())
            
            if file_path.suffix.lower() == '.gpkg':
                file_path = utils.ensure_usable_gpkg(file_path)
                layers = utils.list_layers_safe(file_path)
                layer = st.selectbox("Select Layer", layers) if len(layers) > 1 else layers[0]
                uploaded_gdf = utils.read_layer_any(file_path, layer)
            else:
                uploaded_gdf = gpd.read_file(file_path)
            
            if uploaded_gdf.crs is None:
                uploaded_gdf = uploaded_gdf.set_crs(4326)
            
            st.success(f"✅ Loaded {len(uploaded_gdf)} features")
            location = None
    
    st.header("🎨 Style Preset")
    preset = st.selectbox("Choose Style", [
        "Minimal (B&W)",
        "Vibrant Colors",
        "Watercolor",
        "Blueprint",
        "Neon Night",
        "Vintage Map",
        "Pastel Dream",
        "Dark Mode",
        "Satellite Style",
        "Hand Drawn",
        "Cyberpunk",
        "Nature",
        "Custom"
    ])
    
    st.header("🗺️ Map Elements")
    show_buildings = st.checkbox("Buildings", value=True)
    show_streets = st.checkbox("Streets", value=True)
    show_water = st.checkbox("Water Bodies", value=True)
    show_green = st.checkbox("Green Spaces", value=True)
    show_railways = st.checkbox("Railways", value=False)
    show_amenities = st.checkbox("Amenities (POIs)", value=False)
    
    st.header("⚙️ Advanced Options")
    building_height = st.checkbox("3D Building Effect", value=False)
    street_width_var = st.slider("Street Width Variation", 0.5, 3.0, 1.0, 0.1)
    edge_style = st.selectbox("Edge Style", ["Solid", "Dashed", "Dotted", "None"])
    add_texture = st.checkbox("Add Texture/Noise", value=False)

# Style presets with professional palettes
style_presets = {
    "Minimal (B&W)": {
        'background': '#FFFFFF',
        'perimeter': '#000000',
        'streets': {'fc': '#2F3737', 'width': 1.5},
        'building': {'palette': ['#433633', '#666666'], 'edge': '#2F3737', 'alpha': 0.9},
        'water': {'fc': '#E8E8E8', 'alpha': 0.8},
        'green': {'fc': '#D3D3D3', 'alpha': 0.7},
    },
    "Vibrant Colors": {
        'background': '#FFF9E6',
        'perimeter': '#FF6B6B',
        'streets': {'fc': '#4ECDC4', 'width': 2.0},
        'building': {'palette': ['#FF6B6B', '#FFE66D', '#4ECDC4', '#95E1D3'], 'edge': '#2C3E50', 'alpha': 0.85},
        'water': {'fc': '#3498DB', 'alpha': 0.7},
        'green': {'fc': '#2ECC71', 'alpha': 0.6},
    },
    "Watercolor": {
        'background': '#FFF8DC',
        'perimeter': '#8B7355',
        'streets': {'fc': '#D2B48C', 'width': 1.2},
        'building': {'palette': ['#F4A460', '#DEB887', '#D2691E', '#CD853F'], 'edge': '#8B7355', 'alpha': 0.6},
        'water': {'fc': '#87CEEB', 'alpha': 0.5},
        'green': {'fc': '#9ACD32', 'alpha': 0.5},
    },
    "Blueprint": {
        'background': '#003366',
        'perimeter': '#FFFFFF',
        'streets': {'fc': '#FFFFFF', 'width': 1.0},
        'building': {'palette': ['#FFFFFF'], 'edge': '#FFFFFF', 'alpha': 0.8},
        'water': {'fc': '#0066CC', 'alpha': 0.6},
        'green': {'fc': '#004080', 'alpha': 0.5},
    },
    "Neon Night": {
        'background': '#0a0a0a',
        'perimeter': '#00ff00',
        'streets': {'fc': '#ff00ff', 'width': 2.5},
        'building': {'palette': ['#00ffff', '#ff00ff', '#ffff00', '#00ff00'], 'edge': '#00ff00', 'alpha': 0.9},
        'water': {'fc': '#0000ff', 'alpha': 0.7},
        'green': {'fc': '#00ff00', 'alpha': 0.6},
    },
    "Vintage Map": {
        'background': '#F5E6D3',
        'perimeter': '#8B4513',
        'streets': {'fc': '#A0522D', 'width': 1.3},
        'building': {'palette': ['#CD853F', '#DEB887', '#D2B48C'], 'edge': '#8B4513', 'alpha': 0.8},
        'water': {'fc': '#4682B4', 'alpha': 0.6},
        'green': {'fc': '#6B8E23', 'alpha': 0.5},
    },
    "Pastel Dream": {
        'background': '#FFF5F7',
        'perimeter': '#FFB6C1',
        'streets': {'fc': '#DDA0DD', 'width': 1.5},
        'building': {'palette': ['#FFB6C1', '#B0E0E6', '#98FB98', '#FFE4B5'], 'edge': '#D3D3D3', 'alpha': 0.7},
        'water': {'fc': '#B0E0E6', 'alpha': 0.6},
        'green': {'fc': '#98FB98', 'alpha': 0.5},
    },
    "Dark Mode": {
        'background': '#1a1a1a',
        'perimeter': '#ffffff',
        'streets': {'fc': '#4a4a4a', 'width': 1.8},
        'building': {'palette': ['#2c2c2c', '#3a3a3a', '#4a4a4a'], 'edge': '#5a5a5a', 'alpha': 0.9},
        'water': {'fc': '#1e3a5f', 'alpha': 0.7},
        'green': {'fc': '#2d4a2b', 'alpha': 0.6},
    },
    "Satellite Style": {
        'background': '#0d1117',
        'perimeter': '#58a6ff',
        'streets': {'fc': '#8b949e', 'width': 1.2},
        'building': {'palette': ['#30363d', '#484f58', '#6e7681'], 'edge': '#8b949e', 'alpha': 0.85},
        'water': {'fc': '#1f6feb', 'alpha': 0.6},
        'green': {'fc': '#238636', 'alpha': 0.5},
    },
    "Hand Drawn": {
        'background': '#FFFEF2',
        'perimeter': '#2C2416',
        'streets': {'fc': '#5C4A3A', 'width': 1.8},
        'building': {'palette': ['#8B7355', '#A0826D', '#B8956A'], 'edge': '#2C2416', 'alpha': 0.75},
        'water': {'fc': '#7FCDCD', 'alpha': 0.6},
        'green': {'fc': '#A8C686', 'alpha': 0.5},
    },
    "Cyberpunk": {
        'background': '#0f0f23',
        'perimeter': '#ff00ff',
        'streets': {'fc': '#00ffff', 'width': 2.2},
        'building': {'palette': ['#ff00ff', '#00ffff', '#ffff00', '#ff0080'], 'edge': '#ffffff', 'alpha': 0.9},
        'water': {'fc': '#0080ff', 'alpha': 0.7},
        'green': {'fc': '#00ff80', 'alpha': 0.6},
    },
    "Nature": {
        'background': '#E8F5E9',
        'perimeter': '#2E7D32',
        'streets': {'fc': '#8D6E63', 'width': 1.4},
        'building': {'palette': ['#A1887F', '#BCAAA4', '#D7CCC8'], 'edge': '#6D4C41', 'alpha': 0.8},
        'water': {'fc': '#64B5F6', 'alpha': 0.6},
        'green': {'fc': '#66BB6A', 'alpha': 0.7},
    }
}

if preset != "Custom":
    palette = style_presets[preset]
else:
    st.sidebar.subheader("🎨 Custom Colors")
    bg_color = st.sidebar.color_picker("Background", "#FFFFFF")
    street_color = st.sidebar.color_picker("Streets", "#2F3737")
    building_color = st.sidebar.color_picker("Buildings", "#433633")
    water_color = st.sidebar.color_picker("Water", "#a8e1e6")
    green_color = st.sidebar.color_picker("Green Spaces", "#8BB174")
    
    palette = {
        'background': bg_color,
        'streets': {'fc': street_color, 'width': 1.5},
        'building': {'palette': [building_color], 'edge': '#000000', 'alpha': 0.8},
        'water': {'fc': water_color, 'alpha': 0.7},
        'green': {'fc': green_color, 'alpha': 0.6},
    }

# Generate map
if st.button("🎨 Generate Artistic Map", type="primary", use_container_width=True):
    with st.spinner("🎨 Creating your professional artistic map..."):
        try:
            fig, ax = plt.subplots(figsize=(14, 14), constrained_layout=True, 
                                  facecolor=palette['background'])
            ax.set_facecolor(palette['background'])
            
            if input_method == "Upload GeoJSON":
                # Plot uploaded GeoJSON
                uploaded_gdf.plot(ax=ax, 
                                facecolor=palette['building']['palette'][0], 
                                edgecolor=palette['building']['edge'],
                                linewidth=0.8, alpha=palette['building']['alpha'])
                
            else:
                # Download OSM data
                if input_method == "Bounding Box":
                    point = None
                elif isinstance(location, str):
                    point = ox.geocode(location)
                else:
                    point = location
                
                # Buildings
                if show_buildings:
                    try:
                        if input_method == "Bounding Box":
                            buildings = ox.features_from_bbox(bbox, tags={'building': True})
                        else:
                            buildings = ox.features_from_point(point, tags={'building': True}, dist=radius)
                        
                        if not buildings.empty:
                            for idx, building in buildings.iterrows():
                                color = np.random.choice(palette['building']['palette'])
                                
                                if building_height and 'height' in building:
                                    # 3D effect with shadow
                                    offset = 0.00002
                                    shadow = building.geometry.buffer(offset)
                                    gpd.GeoSeries([shadow]).plot(ax=ax, facecolor='#000000', alpha=0.3, zorder=1)
                                
                                gpd.GeoSeries([building.geometry]).plot(
                                    ax=ax, facecolor=color,
                                    edgecolor=palette['building']['edge'],
                                    linewidth=0.5 if edge_style != "None" else 0,
                                    linestyle='--' if edge_style == "Dashed" else (':' if edge_style == "Dotted" else '-'),
                                    alpha=palette['building']['alpha'],
                                    zorder=2
                                )
                    except Exception as e:
                        st.warning(f"Buildings: {str(e)}")
                
                # Streets
                if show_streets:
                    try:
                        if input_method == "Bounding Box":
                            G = ox.graph_from_bbox(bbox, network_type='all')
                        else:
                            G = ox.graph_from_point(point, dist=radius, network_type='all')
                        
                        edges = ox.graph_to_gdfs(G, nodes=False)
                        edges.plot(ax=ax, 
                                  color=palette['streets']['fc'],
                                  linewidth=palette['streets']['width'] * street_width_var,
                                  alpha=0.9, zorder=3)
                    except Exception as e:
                        st.warning(f"Streets: {str(e)}")
                
                # Water
                if show_water:
                    try:
                        if input_method == "Bounding Box":
                            water = ox.features_from_bbox(bbox, tags={'natural': 'water'})
                        else:
                            water = ox.features_from_point(point, tags={'natural': 'water'}, dist=radius)
                        
                        if not water.empty:
                            water.plot(ax=ax, facecolor=palette['water']['fc'],
                                     edgecolor='none', alpha=palette['water']['alpha'], zorder=1)
                    except Exception as e:
                        pass
                
                # Green spaces
                if show_green:
                    try:
                        if input_method == "Bounding Box":
                            green = ox.features_from_bbox(bbox, tags={'landuse': ['grass', 'forest', 'park', 'garden']})
                        else:
                            green = ox.features_from_point(point, tags={'landuse': ['grass', 'forest', 'park', 'garden']}, dist=radius)
                        
                        if not green.empty:
                            green.plot(ax=ax, facecolor=palette['green']['fc'],
                                     edgecolor='none', alpha=palette['green']['alpha'], zorder=1)
                    except Exception as e:
                        pass
                
                # Railways
                if show_railways:
                    try:
                        if input_method == "Bounding Box":
                            railway = ox.features_from_bbox(bbox, tags={'railway': True})
                        else:
                            railway = ox.features_from_point(point, tags={'railway': True}, dist=radius)
                        
                        if not railway.empty:
                            railway.plot(ax=ax, color='#666666', linewidth=1.5, alpha=0.7, zorder=3)
                    except Exception as e:
                        pass
                
                # Amenities (POIs)
                if show_amenities:
                    try:
                        if input_method == "Bounding Box":
                            amenities = ox.features_from_bbox(bbox, tags={'amenity': True})
                        else:
                            amenities = ox.features_from_point(point, tags={'amenity': True}, dist=radius)
                        
                        if not amenities.empty:
                            amenities.plot(ax=ax, color='red', markersize=20, alpha=0.6, zorder=4)
                    except Exception as e:
                        pass
            
            # Add texture/noise if requested
            if add_texture:
                xlim = ax.get_xlim()
                ylim = ax.get_ylim()
                noise = np.random.rand(100, 100) * 0.1
                ax.imshow(noise, extent=[xlim[0], xlim[1], ylim[0], ylim[1]], 
                         cmap='gray', alpha=0.05, zorder=0)
            
            ax.axis('off')
            ax.set_xlim(ax.get_xlim())
            ax.set_ylim(ax.get_ylim())
            ax.set_aspect('equal')
            
            # Title
            if input_method == "Upload GeoJSON":
                title_text = f"Custom Map - {up.name}"
            elif input_method == "Bounding Box":
                title_text = f"Custom Area Map"
            else:
                title_text = location if isinstance(location, str) else f"Lat: {location[0]:.4f}, Lon: {location[1]:.4f}"
            
            fig.suptitle(title_text, fontsize=20, fontweight='bold', y=0.98, 
                        color=palette.get('perimeter', '#000000'))
            
            # Credits
            plt.figtext(0.99, 0.01, f"Author: Alfrick Onyinkwa | Style: {preset}", 
                       ha='right', fontsize=9, style='italic',
                       color=palette.get('perimeter', '#000000'))
            
            st.pyplot(fig)
            
            # Export options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                buf_png = io.BytesIO()
                plt.savefig(buf_png, format='png', dpi=300, bbox_inches='tight', 
                           facecolor=palette['background'])
                buf_png.seek(0)
                st.download_button("⬇️ PNG (300 DPI)", data=buf_png, 
                                 file_name="artistic_map.png", mime="image/png",
                                 use_container_width=True)
            
            with col2:
                buf_svg = io.BytesIO()
                plt.savefig(buf_svg, format='svg', bbox_inches='tight', 
                           facecolor=palette['background'])
                buf_svg.seek(0)
                st.download_button("⬇️ SVG (Vector)", data=buf_svg, 
                                 file_name="artistic_map.svg", mime="image/svg+xml",
                                 use_container_width=True)
            
            with col3:
                buf_pdf = io.BytesIO()
                plt.savefig(buf_pdf, format='pdf', bbox_inches='tight', 
                           facecolor=palette['background'])
                buf_pdf.seek(0)
                st.download_button("⬇️ PDF (Print)", data=buf_pdf, 
                                 file_name="artistic_map.pdf", mime="application/pdf",
                                 use_container_width=True)
            
            plt.close(fig)
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Try: Different location, smaller radius, or check internet connection")

# Examples and tips
with st.expander("📍 Example Locations"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Famous Landmarks:**
        - Times Square, New York City
        - Eiffel Tower, Paris
        - Colosseum, Rome
        - Big Ben, London
        - Tokyo Tower, Tokyo
        """)
    with col2:
        st.markdown("""
        **Urban Areas:**
        - Central Park, New York
        - Hyde Park, London
        - Shibuya, Tokyo
        - Las Ramblas, Barcelona
        - Champs-Élysées, Paris
        """)

with st.expander("💡 Pro Tips"):
    st.markdown("""
    - **For detailed maps**: Use smaller radius (100-500m)
    - **For city overviews**: Use larger radius (1000-5000m)
    - **Bounding Box**: Perfect for custom rectangular areas
    - **Upload GeoJSON**: Use your own data for complete control
    - **3D Effect**: Enable for modern architectural visualization
    - **Texture**: Adds organic, hand-drawn feel
    - **Export SVG**: For editing in Adobe Illustrator
    """)
