# GeoViz Studio
**Code/Author**: Alfrick Onyinkwa

Robust geospatial visualization tool that reads **GPKG/GeoJSON/zipped Shapefile**, auto‑detects layers & numeric columns, offers **Quantile / Equal Interval / Jenks** classes, **ColorBrewer‑style palettes**, and a **Datawrapper‑style legend**. Includes **automatic GPKG repair** (sqlite VACUUM, pyogrio rewrite, ogr2ogr if installed).

## Features
- **Interactive Maps**: Choropleth maps with custom tooltips and legends.
- **Chart Builder**: Create Bar, Scatter, Line, Pie, and Sunburst charts.
- **Data Table**: Searchable, sortable table with mini-charts.
- **Export**: High-resolution PNG maps, interactive HTML, and GeoJSON.

## Windows Quick Start

### Pip (if your GDAL stack is OK)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py

### Conda (recommended)
conda create -n geoviz -c conda-forge python=3.11 geopandas=0.14.4 pyogrio folium streamlit mapclassify altair plotly -y
conda activate geoviz
pip install streamlit-folium
streamlit run app.py

Then open the URL (http://localhost:8501).

## Notes
- GPKG auto‑repair attempts: sqlite VACUUM → pyogrio rewrite → ogr2ogr (if available).
- Reprojects to **EPSG:4326** for web display.
- Zipped shapefile must include .shp, .shx, .dbf (and ideally .prj).
- Use **Quantile** for balanced colors; **Jenks** for natural groupings.

## Exports
- Styled GeoJSON (class + color)
- Interactive HTML (Leaflet)
- High-res PNG (Matplotlib)

