#!/usr/bin/env python3

import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, LineString
import json
import os
import math


def extract_districts_from_kml(kml_path):
    # Register the KML namespace
    ns = {"kml": "http://www.opengis.net/kml/2.2"}

    # Parse the KML file
    tree = ET.parse(kml_path)
    root = tree.getroot()

    districts = {}

    # Find all placemarks
    for placemark in root.findall(".//kml:Placemark", ns):
        # Extract district ID
        name_elem = placemark.find("./kml:name", ns)
        if name_elem is None:
            continue
        district_id = name_elem.text

        # Extract polygon coordinates
        coords_elem = placemark.find(".//kml:coordinates", ns)
        if coords_elem is None:
            continue

        # Parse coordinates into points
        coords_text = coords_elem.text.strip()
        points = []

        for point in coords_text.split():
            parts = point.split(",")
            if len(parts) >= 2:
                lon, lat = float(parts[0]), float(parts[1])
                points.append((lon, lat))

        # Create Shapely polygon
        if len(points) > 2:  # Need at least 3 points for a polygon
            districts[district_id] = Polygon(points)
            if not districts[district_id].is_valid:
                districts[district_id] = districts[district_id].buffer(0)  # Fix self-intersections

    return districts


def find_district_intersections(districts):
    """
    Find all points where multiple districts intersect.
    Returns a dict of point coordinates to list of district IDs that share that point.
    """
    from shapely.geometry import Point
    from collections import defaultdict

    corners = defaultdict(list)

    # Extract the vertices (corners) from each district polygon
    print("Extracting vertices from polygons...")
    for district_id, polygon in districts.items():
        # Get exterior coordinates
        for x, y in polygon.exterior.coords:
            # Round coordinates to handle floating point precision issues
            key = (round(x, 6), round(y, 6))
            corners[key].append(district_id)

        # Get any interior hole coordinates
        for interior in polygon.interiors:
            for x, y in interior.coords:
                key = (round(x, 6), round(y, 6))
                corners[key].append(district_id)

    # Keep only points where 3 or more unique districts meet
    multi_corners = {point: districts for point, districts in corners.items() if len(set(districts)) >= 3}

    print(f"Found {len(multi_corners)} points where 3 or more unique districts meet")
    return multi_corners


def find_adjacent_districts(districts):
    adjacency = {}

    # Initialize adjacency list for each district
    for district_id in districts:
        adjacency[district_id] = []

    # Find multi-district intersection points (potential quadripoints)
    multi_corners = find_district_intersections(districts)

    # Dictionary to track pairs to exclude (opposite corners of quadripoints)
    exclude_pairs = set()

    # Map from quadripoints to districts that meet there
    quadripoints = {}

    # Identify quadripoints
    for point, district_ids in multi_corners.items():
        unique_districts = set(district_ids)
        if len(unique_districts) >= 4:
            # For points with 4+ unique districts, these are quadripoints
            sorted_districts = sorted(list(unique_districts))
            print(f"Found potential quadripoint with districts: {sorted_districts}")
            quadripoints[point] = sorted_districts

            # For each multi-point, we need to identify which districts are not adjacent
            # (i.e., they only meet at this point)
            if len(unique_districts) >= 4:
                # We need to determine the arrangement of districts around this point
                # using geometric analysis to find their relative positions

                # Extract the districts at this point
                districts_at_point = list(unique_districts)

                # Get the center of each district (for simple approximation)
                centers = {}
                for district_id in districts_at_point:
                    polygon = districts[district_id]
                    centroid = polygon.centroid
                    centers[district_id] = (centroid.x, centroid.y)

                # Calculate angles from the intersection point to each district centroid
                angles = {}
                for district_id in districts_at_point:
                    dx = centers[district_id][0] - point[0]
                    dy = centers[district_id][1] - point[1]
                    angle = math.atan2(dy, dx)
                    angles[district_id] = angle

                # Sort districts by their angle around the point (clockwise or counterclockwise)
                sorted_by_angle = sorted(districts_at_point, key=lambda d: angles[d])

                # For a point with n districts, districts that are not adjacent on the
                # perimeter should not be considered adjacent
                diags = []

                if len(unique_districts) == 4:
                    # For quadripoints: districts opposite each other are at index 0,2 and 1,3
                    diags = [
                        (sorted_by_angle[0], sorted_by_angle[2]),
                        (sorted_by_angle[1], sorted_by_angle[3]),
                    ]
                elif len(unique_districts) == 5:
                    # For quintipoints: non-adjacent districts are those separated by at least one district
                    diags = [
                        (sorted_by_angle[0], sorted_by_angle[2]),
                        (sorted_by_angle[0], sorted_by_angle[3]),
                        (sorted_by_angle[1], sorted_by_angle[3]),
                        (sorted_by_angle[1], sorted_by_angle[4]),
                        (sorted_by_angle[2], sorted_by_angle[4]),
                    ]
                elif len(unique_districts) > 5:
                    # For points with more than 5 districts, generate all non-adjacent pairs
                    n = len(sorted_by_angle)
                    for i in range(n):
                        for j in range(i + 2, min(i + n - 1, i + n // 2 + 1)):
                            diags.append((sorted_by_angle[i], sorted_by_angle[j % n]))

                # Rather than hardcoding exceptions, check if the districts actually share a boundary
                # This is a more general way to determine if districts meeting at a point
                # should be considered adjacent
                filtered_diags = []
                for d1, d2 in diags:
                    # Check if these two districts share a boundary anywhere
                    poly1 = districts[d1]
                    poly2 = districts[d2]
                    intersection = poly1.intersection(poly2)

                    # If they share a line segment (not just a point), they're adjacent regardless
                    # of their arrangement around this particular point
                    if intersection.geom_type in ["LineString", "MultiLineString"] or hasattr(intersection, "length") and intersection.length > 0:
                        print(f"  Districts {d1} and {d2} meet diagonally at this point but also share a boundary elsewhere, keeping them adjacent")
                    else:
                        # Only exclude truly diagonal districts that only meet at this point
                        filtered_diags.append((d1, d2))

                diags = filtered_diags

                for d1, d2 in diags:
                    exclude_pairs.add((d1, d2))
                    exclude_pairs.add((d2, d1))
                print(f"  Districts arranged around point: {sorted_by_angle}")
                print(f"  Marked non-adjacent pairs for exclusion: {diags}")

    # Check each pair of districts
    district_ids = list(districts.keys())
    total_pairs = len(district_ids) * (len(district_ids) - 1) // 2
    processed = 0
    skipped = 0

    print(f"Processing {total_pairs} district pairs...")

    for i in range(len(district_ids)):
        for j in range(i + 1, len(district_ids)):
            id_a = district_ids[i]
            id_b = district_ids[j]

            processed += 1
            if processed % 10000 == 0:
                print(f"Processed {processed}/{total_pairs} pairs ({processed/total_pairs*100:.1f}%), skipped {skipped}")

            # Skip if this pair is in the exclude list
            if (id_a, id_b) in exclude_pairs or (id_b, id_a) in exclude_pairs:
                skipped += 1
                continue

            # Quick check if polygons are far apart using bounding boxes
            bbox_a = districts[id_a].bounds
            bbox_b = districts[id_b].bounds

            # Calculate maximum possible distance between bounding boxes
            min_x_a, min_y_a, max_x_a, max_y_a = bbox_a
            min_x_b, min_y_b, max_x_b, max_y_b = bbox_b

            # If bounding boxes are far apart, skip the detailed check
            # Using a threshold of 0.01 degrees (roughly 1.1 km at the equator)
            if min_x_a > max_x_b + 0.01 or max_x_a < min_x_b - 0.01 or min_y_a > max_y_b + 0.01 or max_y_a < min_y_b - 0.01:
                skipped += 1
                continue

            # Buffer polygons slightly to handle numerical precision issues
            buffered_a = districts[id_a].buffer(0.00001)
            buffered_b = districts[id_b].buffer(0.00001)

            # Check if they share a boundary or a point
            if buffered_a.intersects(buffered_b):
                intersection = buffered_a.intersection(buffered_b)

                # Consider adjacent only if they share a boundary line
                if intersection.geom_type in ["LineString", "MultiLineString"] or (hasattr(intersection, "length") and intersection.length > 0):
                    # Add to adjacency lists
                    adjacency[id_a].append(id_b)
                    adjacency[id_b].append(id_a)
                # This else branch should logically never execute now, but keeping structure for safety
                elif intersection.geom_type == "Point" or intersection.geom_type == "MultiPoint":
                    # They only share a point - look if these belong to a quadripoint
                    point_coords = None
                    if intersection.geom_type == "Point":
                        point_coords = (
                            round(intersection.x, 6),
                            round(intersection.y, 6),
                        )
                    elif intersection.geom_type == "MultiPoint":
                        # For MultiPoint, we need to check each point
                        point_coords = [(round(p.x, 6), round(p.y, 6)) for p in intersection.geoms]

                    # Check if these districts meet at a multi-corner and don't share a boundary
                    for corner, corner_districts in multi_corners.items():
                        # For point intersections
                        if (
                            point_coords
                            and isinstance(point_coords, tuple)
                            and abs(corner[0] - point_coords[0]) < 0.000001
                            and abs(corner[1] - point_coords[1]) < 0.000001
                            and id_a in corner_districts
                            and id_b in corner_districts
                            and len(set(corner_districts)) >= 4
                        ):  # Only exclude for quadripoints (4+ unique districts)

                            # Found a quadripoint where both districts meet
                            print(f"Districts {id_a} and {id_b} meet at a corner with {len(corner_districts)} districts, not considering adjacent")
                            # Mark the pair to exclude
                            exclude_pairs.add((id_a, id_b))
                            break

                        # For multi-point intersections, check each point
                        elif point_coords and isinstance(point_coords, list):
                            for p in point_coords:
                                if (
                                    abs(corner[0] - p[0]) < 0.000001 and abs(corner[1] - p[1]) < 0.000001 and id_a in corner_districts and id_b in corner_districts and len(set(corner_districts)) >= 4
                                ):  # Only exclude for quadripoints (4+ unique districts)

                                    # Found a quadripoint
                                    print(f"Districts {id_a} and {id_b} meet at a multipoint corner with {len(corner_districts)} districts, not considering adjacent")
                                    # Mark the pair to exclude
                                    exclude_pairs.add((id_a, id_b))
                                    break

    print(f"Excluded {len(exclude_pairs)} district pairs that only meet at corners")
    return adjacency


def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define input and output paths
    kml_path = os.path.join(script_dir, "../intermediate_data/ge2025_polling_districts_fixed.kml")
    output_path = os.path.join(
        script_dir,
        "../intermediate_data/ge2025_polling_districts_to_adjacent_districts.json",
    )

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

    # Sort the adjacency lists and create a sorted dictionary by district ID
    sorted_adjacency = {}
    for district_id in sorted(adjacency.keys()):
        sorted_adjacency[district_id] = sorted(adjacency[district_id])

    # Write to JSON
    print(f"Writing results to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(sorted_adjacency, f, indent=2)

    print("Done!")


if __name__ == "__main__":
    main()
