import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import osmnx as ox
import tempfile
from pathlib import Path
import utils
import matplotlib.patches as mpatches
from matplotlib.patches import Circle, Rectangle
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import io
from shapely.geometry import Point, box

st.set_page_config(page_title="Pretty Maps Pro", layout="wide", page_icon="🎨")

st.title("🎨 Pretty Maps Pro - Artistic Cartography Studio")
st.caption("Professional artistic map generation inspired by prettymapp | **Code/Author: Alfrick Onyinkwa**")

# Sidebar
with st.sidebar:
    st.header("📍 Location")
    location = st.text_input("Enter Location", "Praça Ferreira do Amaral, Macau")
    radius = st.slider("Radius (meters)", 100, 5000, 500, 50)
    
    st.header("🎨 Color Theme")
    preset = st.selectbox("Choose Preset", [
        "Peach",
        "Macao",
        "Aubergine", 
        "Minimal (B&W)",
        "Vibrant Colors",
        "Watercolor",
        "Blueprint",
        "Neon Night",
        "Vintage Map",
        "Pastel Dream",
        "Dark Mode",
        "Cyberpunk",
        "Nature",
        "Custom"
    ])
    
    # Customize map style section
    with st.expander("🎨 Customize Map Style"):
        st.subheader("Map Shape")
        map_shape = st.selectbox("Shape", ["Circle", "Rectangle", "Square"], key="map_shape")
        
        st.subheader("Background")
        bg_shape = st.selectbox("Background Shape", ["Circle", "Rectangle", "Square"], key="bg_shape")
        bg_color = st.color_picker("Background Color", "#F2F4CB")
        bg_buffer = st.slider("Background Size", 0, 50, 0, help="Padding around map")
        
        st.subheader("Contour")
        show_contour = st.checkbox("Show Contour", value=True)
        contour_color = st.color_picker("Contour Color", "#2F3737")
        contour_width = st.slider("Contour Width", 0, 20, 0)
        
        st.subheader("Title")
        custom_title = st.text_input("Custom Title", "")
        title_size = st.slider("Title Font Size", 10, 50, 25)
        
        st.subheader("Font Colors")
        title_color = st.color_picker("Title Color", "#2F3737")
        subtitle_color = st.color_picker("Subtitle Color", "#2F3737")
        
        st.subheader("Text Outline")
        text_outline = st.checkbox("Text Outline", value=False)
        if text_outline:
            outline_color = st.color_picker("Outline Color", "#FFFFFF")
            outline_width = st.slider("Outline Width", 1, 10, 3)
    
    st.header("🗺️ Map Elements")
    show_buildings = st.checkbox("Buildings", value=True)
    show_streets = st.checkbox("Streets", value=True)
    show_water = st.checkbox("Water Bodies", value=True)
    show_green = st.checkbox("Green Spaces", value=True)
    show_railways = st.checkbox("Railways", value=False)
    
    st.header("⚙️ Advanced Options")
    dilate = st.slider("Dilate (boundary expansion)", 0, 100, 0)
    street_width_var = st.slider("Street Width", 0.5, 5.0, 1.5, 0.1)
    building_alpha = st.slider("Building Transparency", 0.0, 1.0, 0.7, 0.05)

# Enhanced style presets matching prettymapp
style_presets = {
    "Peach": {
        'background': '#F2F4CB',
        'perimeter': '#2F3737',
        'streets': {'fc': '#2F3737', 'width': 1.5},
        'building': {'palette': ['#FFC3A0', '#FFAFBD', '#FF8C94'], 'edge': '#2F3737', 'alpha': 0.7},
        'water': {'fc': '#a8e1e6', 'alpha': 0.6},
        'green': {'fc': '#8BB174', 'alpha': 0.6},
    },
    "Macao": {
        'background': '#F2F4CB',
        'perimeter': '#2F3737',
        'streets': {'fc': '#2F3737', 'width': 1.5},
        'building': {'palette': ['#433633', '#FF5E5B'], 'edge': '#2F3737', 'alpha': 0.7},
        'water': {'fc': '#a8e1e6', 'alpha': 0.6},
        'green': {'fc': '#8BB174', 'alpha': 0.6},
    },
    "Aubergine": {
        'background': '#EAD7D1',
        'perimeter': '#2F3737',
        'streets': {'fc': '#2F3737', 'width': 1.5},
        'building': {'palette': ['#6C5B7B', '#C06C84', '#F67280'], 'edge': '#2F3737', 'alpha': 0.7},
        'water': {'fc': '#a8e1e6', 'alpha': 0.6},
        'green': {'fc': '#8BB174', 'alpha': 0.6},
    },
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
    # Override with custom settings from expander
    palette['background'] = bg_color
else:
    st.sidebar.subheader("🎨 Custom Colors")
    street_color = st.sidebar.color_picker("Streets", "#2F3737")
    building_color = st.sidebar.color_picker("Buildings", "#433633")
    water_color = st.sidebar.color_picker("Water", "#a8e1e6")
    green_color = st.sidebar.color_picker("Green Spaces", "#8BB174")
    
    palette = {
        'background': bg_color,
        'perimeter': contour_color,
        'streets': {'fc': street_color, 'width': 1.5},
        'building': {'palette': [building_color], 'edge': contour_color, 'alpha': 0.8},
        'water': {'fc': water_color, 'alpha': 0.7},
        'green': {'fc': green_color, 'alpha': 0.6},
    }

# Override building alpha with slider value
palette['building']['alpha'] = building_alpha

# Generate map
if st.button("🎨 Generate Artistic Map", type="primary", use_container_width=True):
    with st.spinner("🎨 Creating your beautiful map..."):
        try:
            # Geocode location
            point = ox.geocode(location)
            
            # Create figure with custom background
            fig, ax = plt.subplots(figsize=(12, 12), facecolor=palette['background'])
            ax.set_facecolor(palette['background'])
            
            # Calculate effective radius with dilate
            effective_radius = radius + dilate
            
            # Track what features were found
            features_found = []
            features_missing = []
            
            # Download OSM data
            # Buildings
            buildings_gdf = None
            if show_buildings:
                try:
                    buildings = ox.features_from_point(point, tags={'building': True}, dist=effective_radius)
                    if not buildings.empty:
                        buildings_gdf = buildings
                        features_found.append("Buildings")
                        for idx, building in buildings.iterrows():
                            color = np.random.choice(palette['building']['palette'])
                            gpd.GeoSeries([building.geometry]).plot(
                                ax=ax, facecolor=color,
                                edgecolor=palette['building']['edge'],
                                linewidth=0.5,
                                alpha=palette['building']['alpha'],
                                zorder=2
                            )
                    else:
                        features_missing.append("Buildings")
                except Exception as e:
                    features_missing.append(f"Buildings ({str(e)[:30]})")
            
            # Streets
            if show_streets:
                try:
                    G = ox.graph_from_point(point, dist=effective_radius, network_type='all')
                    edges = ox.graph_to_gdfs(G, nodes=False)
                    features_found.append("Streets")
                    edges.plot(ax=ax, 
                              color=palette['streets']['fc'],
                              linewidth=palette['streets']['width'] * street_width_var,
                              alpha=0.9, zorder=3)
                except Exception as e:
                    features_missing.append(f"Streets ({str(e)[:30]})")
            
            # Water
            if show_water:
                try:
                    water = ox.features_from_point(point, tags={'natural': 'water'}, dist=effective_radius)
                    if not water.empty:
                        features_found.append("Water")
                        water.plot(ax=ax, facecolor=palette['water']['fc'],
                                 edgecolor='none', alpha=palette['water']['alpha'], zorder=1)
                    else:
                        features_missing.append("Water")
                except Exception as e:
                    features_missing.append("Water")
            
            # Green spaces
            if show_green:
                try:
                    green = ox.features_from_point(point, tags={'landuse': ['grass', 'forest', 'park', 'garden']}, dist=effective_radius)
                    if not green.empty:
                        features_found.append("Green spaces")
                        green.plot(ax=ax, facecolor=palette['green']['fc'],
                                 edgecolor='none', alpha=palette['green']['alpha'], zorder=1)
                    else:
                        features_missing.append("Green spaces")
                except Exception as e:
                    features_missing.append("Green spaces")
            
            # Railways
            if show_railways:
                try:
                    railway = ox.features_from_point(point, tags={'railway': True}, dist=effective_radius)
                    if not railway.empty:
                        railway.plot(ax=ax, color='#666666', linewidth=1.5, alpha=0.7, zorder=3)
                except Exception as e:
                    pass
            
            # Get current axis limits
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            center_x = (xlim[0] + xlim[1]) / 2
            center_y = (ylim[0] + ylim[1]) / 2
            
            # Apply map shape clipping
            if map_shape == "Circle":
                # Create circular clip path
                radius_deg = (xlim[1] - xlim[0]) / 2
                circle = Circle((center_x, center_y), radius_deg, transform=ax.transData)
                for artist in ax.get_children():
                    if hasattr(artist, 'set_clip_path'):
                        artist.set_clip_path(circle)
            elif map_shape == "Square":
                # Make square by using smaller dimension
                size = min(xlim[1] - xlim[0], ylim[1] - ylim[0])
                half_size = size / 2
                ax.set_xlim(center_x - half_size, center_x + half_size)
                ax.set_ylim(center_y - half_size, center_y + half_size)
            # Rectangle is default, no clipping needed
            
            # Add background shape
            if bg_buffer > 0:
                buffer_deg = bg_buffer * 0.00001  # Convert to degrees approximately
                if bg_shape == "Circle":
                    bg_radius = (xlim[1] - xlim[0]) / 2 + buffer_deg
                    bg_circle = Circle((center_x, center_y), bg_radius, 
                                      facecolor=palette['background'], 
                                      edgecolor='none', zorder=0)
                    ax.add_patch(bg_circle)
                elif bg_shape == "Rectangle":
                    bg_rect = Rectangle((xlim[0] - buffer_deg, ylim[0] - buffer_deg),
                                       xlim[1] - xlim[0] + 2*buffer_deg,
                                       ylim[1] - ylim[0] + 2*buffer_deg,
                                       facecolor=palette['background'],
                                       edgecolor='none', zorder=0)
                    ax.add_patch(bg_rect)
                elif bg_shape == "Square":
                    size = min(xlim[1] - xlim[0], ylim[1] - ylim[0]) + 2*buffer_deg
                    bg_square = Rectangle((center_x - size/2, center_y - size/2),
                                         size, size,
                                         facecolor=palette['background'],
                                         edgecolor='none', zorder=0)
                    ax.add_patch(bg_square)
            
            # Add contour
            if show_contour and contour_width > 0:
                if map_shape == "Circle":
                    radius_deg = (xlim[1] - xlim[0]) / 2
                    contour_circle = Circle((center_x, center_y), radius_deg,
                                           facecolor='none',
                                           edgecolor=contour_color,
                                           linewidth=contour_width, zorder=10)
                    ax.add_patch(contour_circle)
                else:
                    # Rectangle/Square contour
                    rect = Rectangle((xlim[0], ylim[0]),
                                    xlim[1] - xlim[0],
                                    ylim[1] - ylim[0],
                                    facecolor='none',
                                    edgecolor=contour_color,
                                    linewidth=contour_width, zorder=10)
                    ax.add_patch(rect)
            
            ax.axis('off')
            ax.set_aspect('equal')
            
            # Add title
            title_text = custom_title if custom_title else location
            if text_outline:
                # Add text with outline effect
                import matplotlib.patheffects as path_effects
                title = fig.suptitle(title_text, fontsize=title_size, fontweight='bold', 
                                    y=0.95, color=title_color)
                title.set_path_effects([
                    path_effects.Stroke(linewidth=outline_width, foreground=outline_color),
                    path_effects.Normal()
                ])
            else:
                fig.suptitle(title_text, fontsize=title_size, fontweight='bold', 
                           y=0.95, color=title_color)
            
            # Credits
            plt.figtext(0.99, 0.01, f"Created with Pretty Maps Pro | Style: {preset}", 
                       ha='right', fontsize=8, style='italic',
                       color=subtitle_color)
            
            st.pyplot(fig)
            
            # Export options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                buf_png = io.BytesIO()
                plt.savefig(buf_png, format='png', dpi=300, bbox_inches='tight', 
                           facecolor=palette['background'], pad_inches=0.2)
                buf_png.seek(0)
                st.download_button("⬇️ Download PNG", data=buf_png, 
                                 file_name=f"{location.replace(' ', '_')}_map.png", 
                                 mime="image/png",
                                 use_container_width=True)
            
            with col2:
                buf_svg = io.BytesIO()
                plt.savefig(buf_svg, format='svg', bbox_inches='tight', 
                           facecolor=palette['background'], pad_inches=0.2)
                buf_svg.seek(0)
                st.download_button("⬇️ Download SVG", data=buf_svg, 
                                 file_name=f"{location.replace(' ', '_')}_map.svg", 
                                 mime="image/svg+xml",
                                 use_container_width=True)
            
            with col3:
                buf_pdf = io.BytesIO()
                plt.savefig(buf_pdf, format='pdf', bbox_inches='tight', 
                           facecolor=palette['background'], pad_inches=0.2)
                buf_pdf.seek(0)
                st.download_button("⬇️ Download PDF", data=buf_pdf, 
                                 file_name=f"{location.replace(' ', '_')}_map.pdf", 
                                 mime="application/pdf",
                                 use_container_width=True)
            
            plt.close(fig)
            
            # Show what was found
            if features_found:
                st.success("✅ Map created with: " + ", ".join(features_found))
            if features_missing:
                st.info("ℹ️ Not available in this area: " + ", ".join(features_missing))
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.info("💡 Try: Different location (e.g., 'Central Park, New York'), smaller radius (100-500m), or check internet connection")

# Examples and tips
with st.expander("📍 Example Locations"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Famous Landmarks:**
        - Praça Ferreira do Amaral, Macau
        - Times Square, New York City
        - Eiffel Tower, Paris
        - Colosseum, Rome
        - Big Ben, London
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
    - **Radius**: Smaller radius (100-500m) for detailed maps, larger (1000-5000m) for city overviews
    - **Map Shape**: Circle for landmarks, Rectangle for streets and neighborhoods
    - **Background Buffer**: Add padding around your map for a cleaner look
    - **Contour**: Add a border to frame your map beautifully
    - **Dilate**: Expand the boundary to include more context around your location
    - **Custom Title**: Add a personalized title to your map
    - **Export SVG**: Perfect for editing in Adobe Illustrator or other vector software
    """)
