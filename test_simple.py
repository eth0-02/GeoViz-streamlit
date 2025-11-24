import sys
print("Hello from python")
import pandas
print("Pandas imported")
try:
    import geopandas
    print("Geopandas imported")
except ImportError:
    print("Geopandas not found")
except Exception as e:
    print(f"Geopandas error: {e}")
