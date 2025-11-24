# Datawrapper-Pro (GPKG-Ready)
import tempfile
from pathlib import Path
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import altair as alt
import utils
import plotly.express as px

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
# 3. Data Loading & Preprocessing
# -----------------------------------------------------------------------------
if not up:
    st.info("Upload a dataset to begin.")
    st.stop()

tmpdir = Path(tempfile.mkdtemp(prefix='dwpro_'))
file_path = tmpdir / up.name
file_path.write_bytes(up.read())

if file_path.suffix.lower() == '.gpkg':
    file_path = utils.ensure_usable_gpkg(file_path)

layers = utils.list_layers_safe(file_path)
layer = st.sidebar.selectbox("Layer", layers, index=0)

try:
    gdf = utils.read_layer_any(file_path, layer)
except Exception as e:
    st.error(f"Could not read the selected layer.\n\nDetails: {e}")
    st.stop()

if gdf.empty:
    st.error("Layer loaded, but it is empty.")
    st.stop()

if gdf.crs is None:
    gdf = gdf.set_crs(4326, allow_override=True)
else:
    gdf = gdf.to_crs(4326)

# Filter out missing geometries to prevent folium error
gdf = gdf[~gdf.geometry.isna() & ~gdf.geometry.is_empty].copy()

# -----------------------------------------------------------------------------
# 4. Main Tabs
# -----------------------------------------------------------------------------
tab_map, tab_charts, tab_table, tab_export = st.tabs(["Map", "Chart Builder", "Data Table", "Export"])

num_cols = utils.numeric_columns(gdf)
str_cols = [c for c in gdf.columns if c != 'geometry' and pd.api.types.is_string_dtype(gdf[c])]

if not num_cols:
    st.error("No numeric columns found in this layer.")
    st.stop()

column = st.sidebar.selectbox("Numeric column to map", num_cols, index=0)

# Clean numeric column
s = pd.to_numeric(gdf[column], errors='coerce')
mask = ~s.isna() & ~s.isin([float('inf'), -float('inf')])
gdf = gdf[mask].copy()
s = pd.to_numeric(gdf[column], errors='coerce')

if gdf.empty:
    st.error("No valid rows after cleaning values for the selected column.")
    st.stop()

# Classification & Colors
cl = utils.classify(s, scheme, classes)
gdf['__class__'] = cl.yb

if palette == "Custom":
    class_colors = custom_colors
else:
    class_colors = utils.get_cmap_hexlist(palette, classes, reverse)

gdf['__color__'] = [class_colors[i] for i in gdf['__class__']]

# -----------------------------------------------------------------------------
# Tab 1: Map
# -----------------------------------------------------------------------------
with tab_map:
    st.subheader("Interactive Map")
    
    # Legend
    vmin, vmax = float(s.min()), float(s.max())
    if palette == "Custom":
        legend_colors = custom_colors
    else:
        legend_colors = utils.get_cmap_hexlist(palette, 9, reverse)

    legend_box = utils.make_continuous_legend_html(legend_colors, vmin, vmax, legend_label)

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

    m = folium.Map(location=zoom_center, zoom_start=zoom_start, tiles=tiles)

    def style_fn(feat):
        return {'color':'#222','weight':0.6,'fillOpacity':opacity,
                'fillColor': feat['properties'].get('__color__', '#cccccc')}

    # Tooltips
    all_cols = [c for c in gdf.columns if c not in ['geometry', '__class__', '__color__']]
    tooltip_cols = st.multiselect("Tooltip columns", all_cols, default=[column])

    folium.GeoJson(
        gdf,
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(fields=tooltip_cols, aliases=tooltip_cols, sticky=False),
        highlight_function=lambda f: {'weight':2}
    ).add_to(m)

    # Legend Marker
    folium.map.Marker(
        [gdf.total_bounds[1], gdf.total_bounds[0]], # Bottom-left approximation
        icon=folium.DivIcon(html=f"""
        <div style='position: fixed; left: 16px; bottom: 18px; z-index: 9999;'>
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

    st_folium(m, height=720, use_container_width=True)

    if map_source:
        st.caption(map_source)

# -----------------------------------------------------------------------------
# Tab 2: Chart Builder
# -----------------------------------------------------------------------------
with tab_charts:
    st.subheader("Chart Builder")
    chart_type = st.selectbox("Chart Type", ["Bar", "Scatter", "Line", "Pie", "Sunburst", "Histogram"])
    
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
