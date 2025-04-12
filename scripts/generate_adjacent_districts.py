#!/usr/bin/env python3

import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, LineString
import json
import os

def extract_districts_from_kml(kml_path):
    # Register the KML namespace
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    # Parse the KML file
    tree = ET.parse(kml_path)
    root = tree.getroot()
    
    districts = {}
    
    # Find all placemarks
    for placemark in root.findall('.//kml:Placemark', ns):
        # Extract district ID
        name_elem = placemark.find('./kml:name', ns)
        if name_elem is None:
            continue
        district_id = name_elem.text
        
        # Extract polygon coordinates
        coords_elem = placemark.find('.//kml:coordinates', ns)
        if coords_elem is None:
            continue
        
        # Parse coordinates into points
        coords_text = coords_elem.text.strip()
        points = []
        
        for point in coords_text.split():
            parts = point.split(',')
            if len(parts) >= 2:
                try:
                    lon, lat = float(parts[0]), float(parts[1])
                    points.append((lon, lat))
                except ValueError:
                    continue
        
        # Create Shapely polygon
        if len(points) > 2:  # Need at least 3 points for a polygon
            try:
                districts[district_id] = Polygon(points)
                if not districts[district_id].is_valid:
                    districts[district_id] = districts[district_id].buffer(0)  # Fix self-intersections
            except Exception as e:
                print(f"Error creating polygon for {district_id}: {e}")
    
    return districts

def find_adjacent_districts(districts):
    adjacency = {}
    
    # Initialize adjacency list for each district
    for district_id in districts:
        adjacency[district_id] = []
    
    # Check each pair of districts
    district_ids = list(districts.keys())
    total_pairs = len(district_ids) * (len(district_ids) - 1) // 2
    processed = 0
    
    print(f"Processing {total_pairs} district pairs...")
    
    for i in range(len(district_ids)):
        for j in range(i+1, len(district_ids)):
            id_a = district_ids[i]
            id_b = district_ids[j]
            
            processed += 1
            if processed % 10000 == 0:
                print(f"Processed {processed}/{total_pairs} pairs ({processed/total_pairs*100:.1f}%)")
            
            try:
                # Buffer polygons slightly to handle numerical precision issues
                buffered_a = districts[id_a].buffer(0.00001)
                buffered_b = districts[id_b].buffer(0.00001)
                
                # Check if they share a boundary (not just a point)
                if buffered_a.intersects(buffered_b):
                    intersection = buffered_a.intersection(buffered_b)
                    
                    # Only consider it adjacent if they share a line segment, not just a point
                    if intersection.geom_type in ['LineString', 'MultiLineString'] or hasattr(intersection, 'length') and intersection.length > 0:
                        adjacency[id_a].append(id_b)
                        adjacency[id_b].append(id_a)
            except Exception as e:
                print(f"Error checking adjacency between {id_a} and {id_b}: {e}")
    
    return adjacency

def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define input and output paths
    kml_path = os.path.join(script_dir, "../processed_data/ge2025_polling_districts_fixed.kml")
    output_path = os.path.join(script_dir, "../processed_data/ge2025_polling_districts_to_adjacent_districts.json")
    
    # Extract districts from KML
    print("Extracting districts from KML...")
    districts = extract_districts_from_kml(kml_path)
    print(f"Extracted {len(districts)} districts")
    
    # Find adjacent districts
    print("Finding adjacent districts...")
    adjacency = find_adjacent_districts(districts)
    
    # Verify results
    isolated = [d for d, adj in adjacency.items() if len(adj) == 0]
    if isolated:
        print(f"Warning: {len(isolated)} districts have no adjacencies:")
        for d in isolated[:10]:
            print(f"  - {d}")
        if len(isolated) > 10:
            print(f"  - (and {len(isolated) - 10} more)")
    
    # Count adjacencies
    total_adjacencies = sum(len(adj) for adj in adjacency.values())
    print(f"Total adjacency relationships: {total_adjacencies}")
    print(f"Average adjacencies per district: {total_adjacencies / len(districts):.2f}")
    
    # Write to JSON
    print(f"Writing results to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(adjacency, f, indent=2)
    
    print("Done!")

if __name__ == "__main__":
    main()