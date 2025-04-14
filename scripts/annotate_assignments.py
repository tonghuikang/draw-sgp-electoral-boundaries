import json
import os
import sys
from shapely.geometry import shape, Polygon, LineString, MultiPolygon
import shapely.ops
import numpy as np
from collections import Counter

from typing import Dict, List, Set, Union, Optional, Any

# Check if running in a virtual environment
in_venv = sys.prefix != sys.base_prefix
if not in_venv:
    print("IMPORTANT: This script requires the shapely and numpy packages.")
    print("Please run with: source .venv/bin/activate && python scripts/annotate_assignments.py")


def load_json(filepath: str) -> Dict[str, Any]:
    with open(filepath, "r") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def is_contiguous(constituency_districts: List[str], adjacency_data: Dict[str, List[str]]) -> bool:
    """Check if a constituency is contiguous using breadth-first search."""
    if not constituency_districts:
        return False

    # Start BFS from the first district
    visited: Set[str] = set()
    queue: List[str] = [constituency_districts[0]]
    visited.add(constituency_districts[0])

    while queue:
        current_district = queue.pop(0)

        # Get adjacent districts that are in the same constituency
        if current_district in adjacency_data:
            for adjacent in adjacency_data[current_district]:
                if adjacent in constituency_districts and adjacent not in visited:
                    visited.add(adjacent)
                    queue.append(adjacent)

    # If all districts are visited, the constituency is contiguous
    return len(visited) == len(constituency_districts)


def calculate_nonenclavity(constituency_districts: List[str], all_constituencies: Dict[str, List[str]], adjacency_data: Dict[str, List[str]]) -> float:
    """
    Calculate nonenclavity as 1 minus (max adjacent constituency count / number of non-enclave polling districts).
    For each polling district that is not an enclave in the constituency, count the adjacent constituencies.
    """
    if not constituency_districts:
        return 0.0

    # Find districts that are not enclaves (have external adjacents)
    non_enclave_count = 0

    # Track count of adjacent districts by constituency
    adjacent_constituency_counts = Counter()

    for district in constituency_districts:
        # Skip if district has no adjacency data
        if district not in adjacency_data:
            continue

        # Get adjacent districts outside the constituency
        external_adjacents = [adj for adj in adjacency_data[district] if adj not in constituency_districts]

        # If no external adjacents, this is an enclave district
        if not external_adjacents:
            continue

        non_enclave_count += 1

        # Count which constituencies the adjacents belong to
        adjacent_constituencies = set()
        for adjacent in external_adjacents:
            # Find which constituency this adjacent district belongs to
            for constituency, districts in all_constituencies.items():
                if adjacent in districts:
                    adjacent_constituencies.add(constituency)

        for adjacent_constituency in adjacent_constituencies:
            adjacent_constituency_counts[adjacent_constituency] += 1 / len(adjacent_constituencies)

    # If all districts are enclaves or there are no districts, return 0
    if non_enclave_count == 0:
        return 0.0

    # Get the maximum adjacent constituency count
    max_adjacent_count = max(adjacent_constituency_counts.values())

    # Calculate the ratio and then the nonenclavity score
    enclavity = max_adjacent_count / non_enclave_count
    allowed_enclavity = 0.5
    if enclavity < allowed_enclavity:
        return 1

    return 1 - (enclavity - allowed_enclavity) / allowed_enclavity


def calculate_geometric_score(a, b):
    if a == 0 or b == 0:
        return 0
    return min(a / b, b / a)


def calculate_compactness(constituency_districts: List[str], geojson_data: Dict[str, Any]) -> Optional[float]:
    """Average geometric score between the chord length of every quarter-degree through the centroid, and the mean chord length"""
    # Extract geometries for the constituency districts
    constituency_features: List[Dict[str, Any]] = [f for f in geojson_data["features"] if f["properties"]["name"] in constituency_districts]

    if not constituency_features:
        return None

    # Create a single geometry for the constituency
    geometries: List[Union[MultiPolygon, Polygon]] = [shape(feature["geometry"]) for feature in constituency_features]
    constituency_geometry: Union[MultiPolygon, Polygon] = shapely.ops.unary_union(geometries)
    # Get the centroid (center of mass) of the polygon
    center = constituency_geometry.centroid
    cx, cy = center.x, center.y

    # Use a large constant to approximate an "infinite" line.
    # Coordinates are latitude and longtitude
    L = 1e5

    chord_lengths = []

    # Iterate through angles from 0 to π (unique directions)
    for theta in np.linspace(0, np.pi, 720):
        dx = np.cos(theta)
        dy = np.sin(theta)
        # Construct a long line through the centroid
        start = (cx - L * dx, cy - L * dy)
        end = (cx + L * dx, cy + L * dy)
        line = LineString([start, end])

        # Find the intersection of the line with the polygon
        inter = constituency_geometry.intersection(line)

        chord_length = 0.0
        if inter.is_empty:
            chord_length = 0.0
        elif inter.geom_type == "LineString":
            chord_length = inter.length
        elif inter.geom_type == "MultiLineString":
            # Should also sum of the nonintersecting
            chord_length = sum(segment.length for segment in inter.geoms)
        elif inter.geom_type == "Point":
            chord_length = 0.0

        chord_lengths.append(chord_length)

    mean_chord_length = np.median(chord_lengths)
    compactness = []
    for chord_length in chord_lengths:
        geometric_score = calculate_geometric_score(chord_length, mean_chord_length)
        compactness.append(geometric_score)
    return sum(compactness) / len(compactness)


def calculate_convexity(constituency_districts: List[str], geojson_data: Dict[str, Any]) -> Optional[float]:
    """Calculate convexity as area of shape over area of convex hull."""
    # Extract geometries for the constituency districts
    constituency_features: List[Dict[str, Any]] = [f for f in geojson_data["features"] if f["properties"]["name"] in constituency_districts]

    if not constituency_features:
        return None

    # Create a single geometry for the constituency
    geometries: List[Union[MultiPolygon, Polygon]] = [shape(feature["geometry"]) for feature in constituency_features]
    constituency_geometry: Union[MultiPolygon, Polygon] = shapely.ops.unary_union(geometries)

    # Calculate area of the constituency
    constituency_area: float = constituency_geometry.area

    convex_hull = shapely.convex_hull(constituency_geometry)

    # Compactness ratio (0 to 1, higher is more compact)
    return constituency_area / convex_hull.area


def get_name_aliases() -> Dict[str, List[str]]:
    """Load name aliases from the aliases file and create a lookup dictionary."""
    with open("raw_data/name_aliases.json", "r") as f:
        alias_groups = json.load(f)

    # Create a dictionary mapping each name to all its equivalent names
    alias_map = {}
    for group in alias_groups:
        for name in group:
            alias_map[name] = group

    return alias_map


def calculate_relevance(constituency_name: str, polling_districts: List[str], geojson_data: Dict[str, Any], district_to_elector_size: Dict[str, int]) -> float:
    """Calculate relevance based on constituency name and MRT station names.

    Score is 1 if constituency name matches either major or minor MRT name for a polling district.
    For double-barrel names (e.g., "Jurong East-Bukit Batok"),
    the minimum relevance score of either part is used.
    The constituency score is the elector weighted average of polling district scores.

    Considers name aliases as defined in raw_data/name_aliases.json.
    """
    total_elector_size = sum(district_to_elector_size.get(district, 0) for district in polling_districts)
    if total_elector_size == 0:
        return 0.0

    # Get name aliases
    name_aliases = get_name_aliases()

    # Extract parts from constituency name
    constituency_parts = [constituency_name]
    if "-" in constituency_name:
        constituency_parts = [part.strip() for part in constituency_name.split("-")]

    # Calculate relevance for each part separately
    part_relevance_scores = []
    for part in constituency_parts:
        part_with_aliases = [part]
        if part in name_aliases:
            part_with_aliases.extend(name_aliases[part])

        # Calculate the relevance score for this part
        part_weighted_score = 0.0
        for district in polling_districts:
            district_score = 0.0
            elector_size = district_to_elector_size.get(district, 0)

            # Find the district in geojson data
            for feature in geojson_data["features"]:
                if feature["properties"]["name"] == district:
                    major_mrt = feature["properties"].get("nearest_major_mrt", {}).get("name", "")
                    minor_mrt = feature["properties"].get("nearest_minor_mrt", {}).get("name", "")

                    # Add aliases for MRT station names
                    major_mrt_aliases = [major_mrt]
                    if major_mrt in name_aliases:
                        major_mrt_aliases.extend(name_aliases[major_mrt])

                    minor_mrt_aliases = [minor_mrt]
                    if minor_mrt in name_aliases:
                        minor_mrt_aliases.extend(name_aliases[minor_mrt])

                    # Check if this part matches any MRT station alias
                    if any(p in major_mrt_aliases or p in minor_mrt_aliases for p in part_with_aliases):
                        district_score = 1.0
                    break

            part_weighted_score += district_score * elector_size

        # Calculate elector weighted average for this part
        part_relevance_scores.append(part_weighted_score / total_elector_size)

    # For single-part names, just return the score
    # For double-barrel names, return the minimum relevance of the parts
    return max(part_relevance_scores) if part_relevance_scores else 0.0


def main() -> None:
    # Load data
    assignment_data = load_json("assignments/official_ge_2025.json")
    adjacency_data = load_json("intermediate_data/ge2025_polling_districts_to_adjacent_districts.json")

    # Load GeoJSON data for compactness calculation
    with open("processed_data/ge2025_polling_districts_with_information.geojson", "r") as f:
        geojson_data = json.load(f)

    # Create mapping of district name to elector size
    district_to_elector_size: Dict[str, int] = {}
    for feature in geojson_data["features"]:
        district_name = feature["properties"]["name"]
        if "elector_size" in feature["properties"]:
            district_to_elector_size[district_name] = feature["properties"]["elector_size"]

    # Organize constituencies and their districts
    constituencies: Dict[str, List[str]] = {}
    for item in assignment_data["assignment"]:
        constituency_name = item["constituency_name"]
        polling_districts = item["polling_districts"]
        constituencies[constituency_name] = polling_districts

    # Analyze each constituency
    results: List[Dict[str, Any]] = []
    for item in assignment_data["assignment"]:
        constituency_name = item["constituency_name"]
        polling_districts = item["polling_districts"]

        # Check if contiguous
        contiguous = is_contiguous(polling_districts, adjacency_data)

        # Calculate nonenclavity
        nonenclavity = calculate_nonenclavity(polling_districts, constituencies, adjacency_data)

        # Calculate compactness
        compactness = calculate_compactness(polling_districts, geojson_data)

        # Calculate total elector size for the constituency
        total_elector_size = sum(district_to_elector_size.get(district, 0) for district in polling_districts)

        # Calculate convexity
        convexity = calculate_convexity(polling_districts, geojson_data)

        # Calculate relevance score
        relevance = calculate_relevance(constituency_name, polling_districts, geojson_data, district_to_elector_size)

        # Add to results
        results.append(
            {
                "constituency_name": constituency_name,
                "member_size": item["member_size"],
                "elector_size": total_elector_size,
                "contiguous": contiguous,
                "nonenclavity": nonenclavity,
                "compactness": compactness,
                "convexity": convexity,
                "relevance": relevance,
            }
        )

    full_elector_size = 0
    full_member_size = 0
    for result in results:
        full_elector_size += result["elector_size"]
        full_member_size += result["member_size"]
    for result in results:
        result["elector_balance"] = calculate_geometric_score(result["elector_size"] / result["member_size"], full_elector_size / full_member_size)

    for result in results:
        overall_score = result["nonenclavity"] + result["compactness"] + result["convexity"] + result["relevance"] + result["elector_balance"]
        result["overall_score"] = overall_score / 5

    # Use the same name as the input file for output
    input_filename = os.path.basename("assignments/official_ge_2025.json")
    output_path = os.path.join("annotations", input_filename)

    # Save results
    save_json({"annotations": results}, output_path)
    print(f"Annotations saved to {output_path}")


if __name__ == "__main__":
    main()
