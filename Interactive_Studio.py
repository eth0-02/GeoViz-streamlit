# Datawrapper-Pro (GPKG-Ready) - Performance Optimized
import tempfile
from pathlib import Path
import streamlit as st
import pandas as pd
import geopandas as gpd
import altair as alt
import utils

# Lazy imports for heavy libraries
# folium, plotly imported only when needed

# -----------------------------------------------------------------------------
# 1. Page Config & Header
# -----------------------------------------------------------------------------
st.set_page_config(page_title="GeoViz Studio", layout="wide")
st.title("GeoViz Studio")
st.caption("Upload a **GPKG / GeoJSON / (zipped) Shapefile**, inspect attributes, then style a **choropleth** with a professional legend. Built for reliability with auto‑repair options for broken GeoPackages.")

with st.expander("About this app"):
    st.markdown("""
    **GeoViz Studio** allows you to visualize geospatial data easily.
    - **Upload**: Support for GPKG, GeoJSON, and zipped Shapefiles.
    - **Repair**: Automatically attempts to repair corrupted GPKG files.
    - **Style**: Choose from various classification schemes and color palettes.
    - **Export**: Download your styled map as GeoJSON, interactive HTML, or high-res PNG.
    
    **Code/Author**: Alfrick Onyinkwa
    """)

# -----------------------------------------------------------------------------
# 2. Sidebar Controls
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("1) Upload")
    up = st.file_uploader("GPKG / GeoJSON / .zip (Shapefile)", type=["gpkg","geojson","json","zip","shp"])
    st.caption("If a GPKG is corrupted, the app will attempt automatic repair (sqlite VACUUM / pyogrio rewrite / ogr2ogr if installed).")
    
    st.header("2) Style")
    classes = st.selectbox("Classes", [5,6,7,8,9], index=0)
    scheme  = st.selectbox("Classification scheme", ["quantile","equalinterval","jenks"], index=0)
    palette = st.selectbox("Color ramp", ["YlGnBu","Blues","Viridis","PuBuGn","Greens","RdYlBu","Spectral","OrRd", "Custom"], index=0)
    
    custom_colors = []
    if palette == "Custom":
        st.subheader("Custom Colors")
        for i in range(classes):
            c = st.color_picker(f"Class {i+1}", value="#cccccc")
            custom_colors.append(c)
    
    reverse = st.checkbox("Reverse colors", value=False)
    legend_label = st.text_input("Legend label", value="Effective Precipitation (mm)")
    
    st.header("3) Map Options")
    tiles = st.selectbox("Map Tiles", ["OpenStreetMap", "CartoDB Positron", "CartoDB Dark_Matter"], index=0)
    opacity = st.slider("Layer Opacity", 0.0, 1.0, 0.85, 0.05)
    
    st.header("4) Metadata")
    map_title = st.text_input("Map Title", value="My Choropleth Map")
    map_subtitle = st.text_input("Subtitle", value="Created with GeoViz Studio")
    map_source = st.text_input("Data Source", value="Source: ...")
    
    st.divider()
    st.markdown("**Code/Author:** Alfrick Onyinkwa")

# -----------------------------------------------------------------------------
# 3. Data Loading & Preprocessing (CACHED FOR PERFORMANCE)
# -----------------------------------------------------------------------------
if not up:
    st.info("Upload a dataset to begin.")
    st.stop()

@st.cache_data(show_spinner="Processing file...")
def load_and_prepare_data(file_bytes, file_name, layer_name, selected_column):
    """Load and prepare geodata with caching for performance."""
    tmpdir = Path(tempfile.mkdtemp(prefix='dwpro_'))
    file_path = tmpdir / file_name
    file_path.write_bytes(file_bytes)
    
    if file_path.suffix.lower() == '.gpkg':
        file_path = utils.ensure_usable_gpkg(file_path)
    
    # Read layer
    gdf = utils.read_layer_any(file_path, layer_name)
    
    if gdf.empty:
        return None, "Layer loaded, but it is empty."
    
    # Set CRS
    if gdf.crs is None:
        gdf = gdf.set_crs(4326, allow_override=True)
    else:
        gdf = gdf.to_crs(4326)
    
    # Filter out missing geometries
    gdf = gdf[~gdf.geometry.isna() & ~gdf.geometry.is_empty].copy()
    
    # Clean numeric column if provided
    if selected_column:
        s = pd.to_numeric(gdf[selected_column], errors='coerce')
        mask = ~s.isna() & ~s.isin([float('inf'), -float('inf')])
        gdf = gdf[mask].copy()
    
    return gdf, None

# Get file bytes once
file_bytes = up.read()

# Get layers
tmpdir = Path(tempfile.mkdtemp(prefix='dwpro_'))
file_path = tmpdir / up.name
file_path.write_bytes(file_bytes)

if file_path.suffix.lower() == '.gpkg':
    file_path = utils.ensure_usable_gpkg(file_path)

layers = utils.list_layers_safe(file_path)
layer = st.sidebar.selectbox("Layer", layers, index=0)

# Get numeric columns for column selection (need to load data first time)
try:
    gdf_temp = utils.read_layer_any(file_path, layer)
    if gdf_temp.crs is None:
        gdf_temp = gdf_temp.set_crs(4326, allow_override=True)
    else:
        gdf_temp = gdf_temp.to_crs(4326)
    num_cols = utils.numeric_columns(gdf_temp)
    str_cols = [c for c in gdf_temp.columns if c != 'geometry' and pd.api.types.is_string_dtype(gdf_temp[c])]
    
    if not num_cols:
        st.error("No numeric columns found in this layer.")
        st.stop()
    
    column = st.sidebar.selectbox("Numeric column to map", num_cols, index=0)
    del gdf_temp  # Free memory
except Exception as e:
    st.error(f"Could not read the selected layer.\n\nDetails: {e}")
    st.stop()

# Load data with caching
gdf, error = load_and_prepare_data(file_bytes, up.name, layer, column)

if error:
    st.error(error)
    st.stop()

if gdf is None or gdf.empty:
    st.error("No valid rows after cleaning values for the selected column.")
    st.stop()

# Recalculate after filtering
s = pd.to_numeric(gdf[column], errors='coerce')

# -----------------------------------------------------------------------------
# 4. Main Tabs
# -----------------------------------------------------------------------------
tab_map, tab_charts, tab_table, tab_export = st.tabs(["Map", "Chart Builder", "Data Table", "Export"])

# Classification & Colors (CACHED)
@st.cache_data(show_spinner=False)
def compute_classification_and_colors(_gdf_hash, column_name, scheme_name, num_classes, palette_name, custom_color_list, reverse_colors):
    """Compute classification and colors with caching. _gdf_hash for cache key."""
    # Get the actual gdf from session state
    gdf_local = st.session_state.get('_gdf_cache')
    if gdf_local is None:
        return None, None, None, None
    
    s = pd.to_numeric(gdf_local[column_name], errors='coerce')
    
    # Classification
    cl = utils.classify(s, scheme_name, num_classes)
    class_assignments = cl.yb
    
    # Colors
    if palette_name == "Custom" and custom_color_list:
        class_colors = custom_color_list
    else:
        class_colors = utils.get_cmap_hexlist(palette_name, num_classes, reverse_colors)
    
    # Assign colors to each row
    color_map = [class_colors[i] for i in class_assignments]
    
    return cl, class_assignments, class_colors, color_map

# Store gdf in session state for caching
if '_gdf_cache' not in st.session_state or st.session_state.get('_file_name') != up.name:
    st.session_state['_gdf_cache'] = gdf
    st.session_state['_file_name'] = up.name

# Create a hash for cache invalidation
gdf_hash = f"{up.name}_{layer}_{len(gdf)}"

cl, class_assignments, class_colors, color_map = compute_classification_and_colors(
    gdf_hash, column, scheme, classes, palette, custom_colors, reverse
)

if cl is None:
    st.error("Error computing classification")
    st.stop()

# Add classification results to gdf
gdf['__class__'] = class_assignments
gdf['__color__'] = color_map

# -----------------------------------------------------------------------------
# Tab 1: Map
# -----------------------------------------------------------------------------
with tab_map:
    st.subheader("Interactive Map")
    
    # Map Controls
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    with col_ctrl1:
        legend_style = st.selectbox("Legend Style", ["Continuous Gradient", "Discrete Classes", "Minimal", "None"])
    with col_ctrl2:
        legend_position = st.selectbox("Legend Position", ["Bottom Left", "Bottom Right", "Top Left", "Top Right"])
    with col_ctrl3:
        fullscreen = st.checkbox("Fullscreen Mode", value=False)
    
    # Legend
    vmin, vmax = float(s.min()), float(s.max())
    if palette == "Custom":
        legend_colors = custom_colors
    else:
        legend_colors = utils.get_cmap_hexlist(palette, 9, reverse)

    # Create legend based on style
    if legend_style == "Continuous Gradient":
        legend_box = utils.make_continuous_legend_html(legend_colors, vmin, vmax, legend_label)
    elif legend_style == "Discrete Classes":
        # Create discrete legend
        legend_items = ""
        for i in range(classes):
            color = class_colors[i]
            bin_min = cl.bins[i-1] if i > 0 else vmin
            bin_max = cl.bins[i]
            legend_items += f"<div style='display:flex; align-items:center; margin:4px 0;'><div style='width:20px; height:20px; background:{color}; border:1px solid #333; margin-right:8px;'></div><span style='font-size:11px;'>{bin_min:.1f} - {bin_max:.1f}</span></div>"
        legend_box = f"""<div style='background:rgba(255,255,255,0.95); padding:12px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);'>
            <div style='font-weight:bold; margin-bottom:8px; font-size:12px;'>{legend_label}</div>
            {legend_items}
        </div>"""
    elif legend_style == "Minimal":
        legend_box = f"""<div style='background:rgba(255,255,255,0.9); padding:8px; border-radius:4px;'>
            <span style='font-size:10px;'>{legend_label}: {vmin:.1f} - {vmax:.1f}</span>
        </div>"""
    else:
        legend_box = ""

    # Search & Annotations Logic
    name_col = st.sidebar.selectbox("Region Name Column (for Search/Labels)", ["(None)"] + str_cols, index=0)

    zoom_center = [(gdf.total_bounds[1] + gdf.total_bounds[3])/2, (gdf.total_bounds[0] + gdf.total_bounds[2])/2]
    zoom_start = 6

    if name_col != "(None)":
        st.sidebar.subheader("Search Region")
        search_term = st.sidebar.selectbox("Find a region", ["(None)"] + sorted(gdf[name_col].astype(str).unique().tolist()))
        if search_term != "(None)":
            selected_row = gdf[gdf[name_col] == search_term]
            if not selected_row.empty:
                bounds = selected_row.total_bounds
                zoom_center = [(bounds[1] + bounds[3])/2, (bounds[0] + bounds[2])/2]
                zoom_start = 10

    annotations = []
    with st.sidebar.expander("Annotations"):
        st.caption("Add markers to the map")
        if name_col != "(None)":
            annot_region = st.selectbox("Select Region to Annotate", ["(None)"] + sorted(gdf[name_col].astype(str).unique().tolist()))
            annot_text = st.text_input("Annotation Text")
            if st.button("Add Annotation") and annot_region != "(None)" and annot_text:
                row = gdf[gdf[name_col] == annot_region].iloc[0]
                pt = row.geometry.centroid
                annotations.append({'lat': pt.y, 'lon': pt.x, 'text': annot_text})
                st.success(f"Added: {annot_text}")

    # Map with plugins (LAZY IMPORTS)
    import folium
    from streamlit_folium import st_folium
    
    m = folium.Map(location=zoom_center, zoom_start=zoom_start, tiles=tiles)
    
    # Add fullscreen button
    if fullscreen:
        from folium.plugins import Fullscreen
        Fullscreen().add_to(m)
    
    # Add draw tools
    from folium.plugins import Draw
    Draw(export=True, draw_options={'polyline': True, 'polygon': True, 'rectangle': True, 'circle': True, 'marker': True}).add_to(m)

    def style_fn(feat):
        return {'color':'#222','weight':0.6,'fillOpacity':opacity,
                'fillColor': feat['properties'].get('__color__', '#cccccc')}

    # Tooltips
    all_cols = [c for c in gdf.columns if c not in ['geometry', '__class__', '__color__']]
    tooltip_cols = st.multiselect("Tooltip columns", all_cols, default=[column] if column in all_cols else [])

    folium.GeoJson(
        gdf,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(fields=tooltip_cols, aliases=tooltip_cols, sticky=False) if tooltip_cols else None,
        highlight_function=lambda f: {'weight':2}
    ).add_to(m)

    # Legend position mapping
    position_map = {
        "Bottom Left": "left: 16px; bottom: 18px;",
        "Bottom Right": "right: 16px; bottom: 18px;",
        "Top Left": "left: 16px; top: 80px;",
        "Top Right": "right: 16px; top: 80px;"
    }
    
    # Legend Marker
    if legend_box:
        folium.map.Marker(
            [gdf.total_bounds[1], gdf.total_bounds[0]],
            icon=folium.DivIcon(html=f"""
            <div style='position: fixed; {position_map[legend_position]} z-index: 9999;'>
              {legend_box}
            </div>""" )
        ).add_to(m)

    # Annotation Markers
    for ann in annotations:
        folium.Marker(
            [ann['lat'], ann['lon']],
            popup=ann['text'],
            tooltip=ann['text'],
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

    st.markdown(f"## {map_title}")
    if map_subtitle:
        st.markdown(f"#### {map_subtitle}")

    map_height = 1000 if fullscreen else 720
    st_folium(m, height=map_height, use_container_width=True)

    if map_source:
        st.caption(map_source)

# -----------------------------------------------------------------------------
# Tab 2: Chart Builder
# -----------------------------------------------------------------------------
with tab_charts:
    st.subheader("Chart Builder")
    chart_type = st.selectbox("Chart Type", [
        "Bar", "Scatter", "Line", "Pie", "Sunburst", "Histogram",
        "Treemap", "Sankey Diagram", "Waterfall", "Funnel", "Box Plot"
    ])
    
    c1, c2 = st.columns(2)
    with c1:
        x_axis = st.selectbox("X Axis (Category/Value)", all_cols, index=0)
    with c2:
        y_axis = st.selectbox("Y Axis (Value)", num_cols, index=0)
    
    color_col = st.selectbox("Color / Group By", ["(None)"] + all_cols)
    
    # Author Credit for Charts
    chart_title = alt.TitleParams(text=f"{chart_type} Chart", subtitle=["Author: Alfrick Onyinkwa"])

    if chart_type == "Bar":
        c = alt.Chart(gdf).mark_bar().encode(
            x=x_axis,
            y=y_axis,
            tooltip=all_cols,
            color=color_col if color_col != "(None)" else alt.value("steelblue")
        ).properties(title=chart_title).interactive()
        st.altair_chart(c, use_container_width=True)
        
    elif chart_type == "Scatter":
        c = alt.Chart(gdf).mark_circle(size=60).encode(
            x=x_axis,
            y=y_axis,
            tooltip=all_cols,
            color=color_col if color_col != "(None)" else alt.value("steelblue")
        ).properties(title=chart_title).interactive()
        st.altair_chart(c, use_container_width=True)
        
    elif chart_type == "Line":
        c = alt.Chart(gdf).mark_line().encode(
            x=x_axis,
            y=y_axis,
            tooltip=all_cols,
            color=color_col if color_col != "(None)" else alt.value("steelblue")
        ).properties(title=chart_title).interactive()
        st.altair_chart(c, use_container_width=True)
        
    elif chart_type == "Pie":
        c = alt.Chart(gdf).mark_arc().encode(
            theta=y_axis,
            color=x_axis,
            tooltip=all_cols
        ).properties(title=chart_title)
        st.altair_chart(c, use_container_width=True)
        
    elif chart_type == "Histogram":
        c = alt.Chart(gdf).mark_bar().encode(
            x=alt.X(y_axis, bin=True),
            y='count()',
            tooltip=[y_axis, 'count()']
        ).properties(title=chart_title).interactive()
        st.altair_chart(c, use_container_width=True)

    elif chart_type == "Sunburst":
        if color_col == "(None)":
            st.warning("Sunburst requires a 'Group By' column for hierarchy.")
        else:
            fig = px.sunburst(gdf, path=[color_col, x_axis], values=y_axis, title="Author: Alfrick Onyinkwa")
            st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Treemap":
        if color_col == "(None)":
            st.warning("Treemap requires a 'Group By' column for hierarchy.")
        else:
            fig = px.treemap(gdf, path=[color_col, x_axis], values=y_axis, title="Treemap - Author: Alfrick Onyinkwa")
            st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Sankey Diagram":
        st.info("Sankey Diagram: Select source and target columns for flow visualization")
        source_col = st.selectbox("Source Column", all_cols, key="sankey_source")
        target_col = st.selectbox("Target Column", all_cols, key="sankey_target")
        
        if source_col and target_col:
            try:
                # Validate that source and target are different
                if source_col == target_col:
                    st.warning("⚠️ Please select different columns for Source and Target")
                else:
                    # Create Sankey data - convert to string to handle any data type
                    sankey_data = gdf[[source_col, target_col, y_axis]].copy()
                    sankey_data[source_col] = sankey_data[source_col].astype(str)
                    sankey_data[target_col] = sankey_data[target_col].astype(str)
                    
                    # Remove any rows with missing values
                    sankey_data = sankey_data.dropna()
                    
                    if sankey_data.empty:
                        st.warning("⚠️ No valid data available for Sankey diagram")
                    else:
                        # Aggregate data
                        sankey_df = sankey_data.groupby([source_col, target_col])[y_axis].sum().reset_index()
                        
                        # Filter out zero or negative values
                        sankey_df = sankey_df[sankey_df[y_axis] > 0]
                        
                        if sankey_df.empty:
                            st.warning("⚠️ No positive values found for flow visualization")
                        else:
                            # Create unique node labels
                            source_nodes = list(sankey_df[source_col].unique())
                            target_nodes = list(sankey_df[target_col].unique())
                            all_nodes = list(dict.fromkeys(source_nodes + target_nodes))  # Preserve order, remove duplicates
                            
                            # Create node index mapping
                            node_dict = {node: idx for idx, node in enumerate(all_nodes)}
                            
                            # Map source and target to indices
                            source_indices = [node_dict[s] for s in sankey_df[source_col]]
                            target_indices = [node_dict[t] for t in sankey_df[target_col]]
                            
                            # Create Sankey diagram
                            fig = px.sankey(
                                data_frame=sankey_df,
                                source=source_indices,
                                target=target_indices,
                                value=sankey_df[y_axis],
                                labels=all_nodes,
                                title="Sankey Diagram - Author: Alfrick Onyinkwa"
                            )
                            
                            # Update layout for better appearance
                            fig.update_layout(
                                font=dict(size=12),
                                height=600
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Show summary statistics
                            st.caption(f"📊 Showing {len(sankey_df)} flows between {len(all_nodes)} nodes")
                            
            except Exception as e:
                st.error(f"❌ Error creating Sankey diagram: {str(e)}")
                st.info("💡 Tip: Ensure your data has categorical columns for source/target and numeric values for flow")
    
    elif chart_type == "Waterfall":
        fig = px.waterfall(gdf, x=x_axis, y=y_axis, title="Waterfall Chart - Author: Alfrick Onyinkwa")
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Funnel":
        fig = px.funnel(gdf, x=y_axis, y=x_axis, title="Funnel Chart - Author: Alfrick Onyinkwa")
        st.plotly_chart(fig, use_container_width=True)
    
    elif chart_type == "Box Plot":
        if color_col != "(None)":
            fig = px.box(gdf, x=color_col, y=y_axis, title="Box Plot - Author: Alfrick Onyinkwa")
        else:
            fig = px.box(gdf, y=y_axis, title="Box Plot - Author: Alfrick Onyinkwa")
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# Tab 3: Data Table & Insights
# -----------------------------------------------------------------------------
with tab_table:
    st.subheader("Editable Data Table")
    st.caption("Edit values below to update the map and charts instantly.")
    
    # Editable Dataframe
    edited_df = st.data_editor(
        gdf.drop(columns=['geometry', '__class__', '__color__']),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            column: st.column_config.ProgressColumn(
                column,
                help=f"Value of {column}",
                format="%.2f",
                min_value=float(s.min()),
                max_value=float(s.max()),
            ),
        }
    )
    
    # Update GDF with edited values (join back geometry)
    # We assume index hasn't changed order, which is true for st.data_editor unless rows added/deleted
    # For simplicity, we just update the columns in gdf
    for col in edited_df.columns:
        gdf[col] = edited_df[col]
    
    # Re-calculate stats based on edited data
    s_edited = pd.to_numeric(gdf[column], errors='coerce')
    
    st.divider()
    st.subheader("Smart Analysis (Automated Insights)")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Count", len(gdf))
    with c2:
        st.metric("Average Value", f"{s_edited.mean():.2f}")
    with c3:
        st.metric("Sum", f"{s_edited.sum():.2f}")
        
    # Find extremes
    if name_col != "(None)":
        max_row = gdf.loc[s_edited.idxmax()]
        min_row = gdf.loc[s_edited.idxmin()]
        st.info(f"**Highest Value**: {max_row[name_col]} ({max_row[column]})")
        st.info(f"**Lowest Value**: {min_row[name_col]} ({min_row[column]})")
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", data=csv, file_name="data.csv", mime="text/csv")

# -----------------------------------------------------------------------------
# Tab 4: Export
# -----------------------------------------------------------------------------
with tab_export:
    st.subheader("Export Static Map")
    
    logo_file = st.file_uploader("Upload Logo (Optional)", type=["png", "jpg", "jpeg"])
    
    if st.button("Generate Static PNG"):
        with st.spinner("Generating high-resolution map..."):
            buf = utils.generate_static_map(
                gdf, 
                column, 
                class_colors, 
                map_title, 
                map_subtitle, 
                map_source, 
                logo_file
            )
            st.image(buf, caption="Preview", width=600)
            st.download_button(
                label="Download PNG",
                data=buf,
                file_name="static_map.png",
                mime="image/png"
            )
    
    st.divider()
    
    st.subheader("Export Interactive Map")
    @st.cache_data
    def export_geojson_cached(_df):
        return utils.export_geojson(_df)

    styled_geojson = export_geojson_cached(gdf)
    st.download_button("Download styled GeoJSON", data=styled_geojson, file_name="choropleth_styled.geojson", mime="application/geo+json")
    html_bytes = m.get_root().render().encode('utf-8')
    st.download_button("Download interactive HTML", data=html_bytes, file_name="map.html", mime="text/html")
