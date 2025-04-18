#!/usr/bin/env python3

import json
import os
import pandas as pd
from fiona import BytesCollection
from fiona.transform import transform_geom
from shapely.geometry import shape, mapping, Point
import kml2geojson
import math

# Paths
input_kml = "../intermediate_data/ge2025_polling_districts_fixed.kml"
elector_size_json = "../intermediate_data/ge2025_polling_distrct_and_estimated_elector_size.json"
adjacent_districts_json = "../intermediate_data/ge2025_polling_districts_to_adjacent_districts.json"
mrt_stations_csv = "../raw_data/mrt_stations.csv"
output_geojson = "../processed_data/ge2025_polling_districts_with_information.geojson"

# Ensure paths are absolute
script_dir = os.path.dirname(os.path.abspath(__file__))
input_kml = os.path.abspath(os.path.join(script_dir, input_kml))
elector_size_json = os.path.abspath(os.path.join(script_dir, elector_size_json))
adjacent_districts_json = os.path.abspath(os.path.join(script_dir, adjacent_districts_json))
mrt_stations_csv = os.path.abspath(os.path.join(script_dir, mrt_stations_csv))
output_geojson = os.path.abspath(os.path.join(script_dir, output_geojson))

print(f"Converting KML to GeoJSON and adding elector sizes, adjacent districts, and nearest MRT stations...")

# Load elector size data
with open(elector_size_json, "r") as f:
    elector_sizes = json.load(f)

# Load adjacent districts data
with open(adjacent_districts_json, "r") as f:
    adjacent_districts = json.load(f)

# Load MRT stations data
mrt_stations = pd.read_csv(mrt_stations_csv)
mrt_stations = mrt_stations[mrt_stations["is_opened"]].reset_index(drop=True).to_dict("records")

# Create a lookup dictionary for faster access
elector_size_dict = {item["polling_district"]: item["estimated_elector_size"] for item in elector_sizes}


# Function to calculate distance between coordinates (in degrees)
def calculate_distance(lat1, lon1, lat2, lon2):
    # Simple Euclidean distance for coordinates in degrees
    # This is sufficient for small areas like Singapore
    return math.sqrt((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2)


# Convert KML to GeoJSON
geojson_data = kml2geojson.convert(input_kml)

# The converted data is a list, we need the features
features = []
for feature_collection in geojson_data:
    for feature in feature_collection["features"]:
        # Extract district code from name property
        district_code = feature.get("properties", {}).get("name")

        if district_code:
            # Add elector size to properties
            feature["properties"]["elector_size"] = elector_size_dict.get(district_code, 0)

            # Add adjacent districts to properties
            feature["properties"]["adjacent_districts"] = adjacent_districts.get(district_code, [])

            # Calculate center of mass for the polygon
            geom = shape(feature["geometry"])
            centroid = geom.centroid
            center_lat, center_lon = centroid.y, centroid.x

            distances = [calculate_distance(center_lat, center_lon, station["lat"], station["long"]) for station in mrt_stations]

            best_ratio = 0
            require_major_station = False
            nearest_mrts = []
            for distance, _, station in sorted(zip(distances, list(range(len(distances))), mrt_stations)):
                distance = max(1e-9, distance)
                ratio = station["passengers"] / distance
                if ratio > best_ratio * (1 - 1 / (len(nearest_mrts) + 1)):
                    nearest_mrts.append(station["name"])
                best_ratio = max(ratio, best_ratio)

            # Add nearest MRT stations to properties
            feature["properties"]["nearest_mrts"] = nearest_mrts

            features.append(feature)

# Create the final GeoJSON structure
final_geojson = {"type": "FeatureCollection", "features": features}

# Save the result with pretty formatting (indent=2)
with open(output_geojson, "w") as f:
    json.dump(final_geojson, f, indent=2)

print(f"Conversion complete. Output saved to {output_geojson}")
