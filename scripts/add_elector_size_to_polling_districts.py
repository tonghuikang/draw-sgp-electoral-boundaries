#!/usr/bin/env python3

import json
import os
from fiona import BytesCollection
from fiona.transform import transform_geom
from shapely.geometry import shape, mapping
import kml2geojson

# Paths
input_kml = "../processed_data/ge2025_polling_districts_fixed.kml"
elector_size_json = "../processed_data/ge2025_polling_distrct_and_estimated_elector_size.json"
adjacent_districts_json = "../processed_data/ge2025_polling_districts_to_adjacent_districts.json"
output_geojson = "../processed_data/ge2025_polling_districts_with_elector_size.geojson"

# Ensure paths are absolute
script_dir = os.path.dirname(os.path.abspath(__file__))
input_kml = os.path.abspath(os.path.join(script_dir, input_kml))
elector_size_json = os.path.abspath(os.path.join(script_dir, elector_size_json))
adjacent_districts_json = os.path.abspath(os.path.join(script_dir, adjacent_districts_json))
output_geojson = os.path.abspath(os.path.join(script_dir, output_geojson))

print(f"Converting KML to GeoJSON and adding elector sizes and adjacent districts...")

# Load elector size data
with open(elector_size_json, 'r') as f:
    elector_sizes = json.load(f)

# Load adjacent districts data
with open(adjacent_districts_json, 'r') as f:
    adjacent_districts = json.load(f)

# Create a lookup dictionary for faster access
elector_size_dict = {item['polling_district']: item['estimated_elector_size'] for item in elector_sizes}

# Convert KML to GeoJSON
geojson_data = kml2geojson.convert(input_kml)

# The converted data is a list, we need the features
features = []
for feature_collection in geojson_data:
    for feature in feature_collection['features']:
        # Extract district code from name property
        district_code = feature.get('properties', {}).get('name')
        
        if district_code:
            # Add elector size to properties
            feature['properties']['elector_size'] = elector_size_dict.get(district_code, 0)
            
            # Add adjacent districts to properties
            feature['properties']['adjacent_districts'] = adjacent_districts.get(district_code, [])
            
            features.append(feature)

# Create the final GeoJSON structure
final_geojson = {
    "type": "FeatureCollection",
    "features": features
}

# Save the result with pretty formatting (indent=2)
with open(output_geojson, 'w') as f:
    json.dump(final_geojson, f, indent=2)

print(f"Conversion complete. Output saved to {output_geojson}")