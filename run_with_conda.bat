@echo off
conda create -n dwpro -c conda-forge python=3.11 geopandas=0.14.4 pyogrio folium streamlit mapclassify -y
call conda activate dwpro
pip install streamlit-folium
streamlit run Interactive_Studio.py
pause
