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
        constituency_parts = list(set(part.strip() for part in constituency_name.split("-")))

    all_match_count = 0
    partial_match_counts = [0 for _ in constituency_parts]
    total_elector_size = 0

    for district in polling_districts:

        matched_constituency_parts = set()

        # Find the district in geojson data
        for feature in geojson_data["features"]:
            if feature["properties"]["name"] == district:
                # Get all MRT station names from the nearest_mrts list
                mrt_stations = feature["properties"].get("nearest_mrts", [])

                # Add aliases for each MRT station name
                for mrt in mrt_stations:
                    if mrt in constituency_parts:
                        matched_constituency_parts.add(mrt)
                    if mrt in name_aliases:
                        for mrt_alias in name_aliases[mrt]:
                            if mrt_alias in constituency_parts:
                                matched_constituency_parts.add(mrt_alias)
                break

        elector_size = district_to_elector_size.get(district, 0)
        total_elector_size += elector_size
        if len(matched_constituency_parts) == len(constituency_parts):
            all_match_count += elector_size
        else:
            for constituency_part in matched_constituency_parts:
                partial_match_counts[constituency_parts.index(constituency_part)] += elector_size

    # probably should just fork the logic for single barrel versus double barrel names?
    numerator = all_match_count + sum(partial_match_count / len(partial_match_counts) ** 0.5 for partial_match_count in partial_match_counts)
    denominator = total_elector_size

    # For single-part names, just return the weighted match ratio.
    # For double-barrel names, it is the weighted sum of the full match ratio,
    # and the weighted sum partial match ratio divided by square root two.
    return numerator / denominator


# Load supporting data
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


def score_assignment(assignment_data: Dict[str, Any]) -> Dict[str, Any]:
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
        constituency_score = (result["nonenclavity"] + result["compactness"] + result["convexity"] + result["relevance"] + result["elector_balance"]) / 5
        # the overall score is upper bounded by elector_balance
        constituency_score = min(constituency_score, result["elector_balance"])
        result["constituency_score"] = constituency_score

    # Calculate overall score as member-weighted average of constituency scores
    overall_score = sum(result["constituency_score"] * result["member_size"] for result in results) / full_member_size

    return {"annotations": results, "overall_score": overall_score}


def validate_assignment(assignment_data: Dict[str, Any]) -> tuple[bool, Dict]:
    """
    Validate that the constituency assignment meets all requirements:
    1. Each constituency is contiguous
    2. All polling districts are assigned exactly once
    3. The elector sizes match the official data
    
    Returns a dictionary with validation results and any errors found.
    """
    # Organize constituencies and their districts
    constituencies: Dict[str, List[str]] = {}
    all_assigned_districts: List[str] = []
    
    for item in assignment_data["assignment"]:
        constituency_name = item["constituency_name"]
        polling_districts = item["polling_districts"]
        constituencies[constituency_name] = polling_districts
        all_assigned_districts.extend(polling_districts)
    
    # Check if all constituencies are contiguous
    non_contiguous = []
    for constituency_name, polling_districts in constituencies.items():
        if not is_contiguous(polling_districts, adjacency_data):
            non_contiguous.append(constituency_name)
    
    # Check if any polling districts are assigned multiple times
    district_counts = Counter(all_assigned_districts)
    duplicate_districts = {district: count for district, count in district_counts.items() if count > 1}
    
    # Check if all polling districts from the data are assigned
    all_known_districts = set(district_to_elector_size.keys())
    unassigned_districts = all_known_districts - set(all_assigned_districts)
    unknown_districts = set(all_assigned_districts) - all_known_districts
    
    # Check total elector size
    total_assigned_electors = sum(district_to_elector_size.get(district, 0) for district in all_assigned_districts)
    total_expected_electors = sum(district_to_elector_size.values())
    
    errors = {
        "non_contiguous_constituencies": non_contiguous,
        "duplicate_districts": duplicate_districts,
        "unassigned_districts": list(unassigned_districts),
        "unknown_districts": list(unknown_districts),
        "total_electors": {
            "assigned": total_assigned_electors,
            "expected": total_expected_electors,
            "difference": total_assigned_electors - total_expected_electors
        }
    }
    
    is_valid = (
        len(non_contiguous) == 0 and
        len(duplicate_districts) == 0 and
        len(unassigned_districts) == 0 and
        len(unknown_districts) == 0 and
        total_assigned_electors == total_expected_electors
    )
    
    return is_valid, errors


def main() -> None:
    # Load data
    assignment_data = load_json("assignments/official_ge_2025.json")

    is_valid, errors = validate_assignment(assignment_data)
    if not is_valid:
        raise ValueError(errors)

    # Score the assignment
    results = score_assignment(assignment_data)

    # Use the same name as the input file for output
    input_filename = os.path.basename("assignments/official_ge_2025.json")
    output_path = os.path.join("annotations", input_filename)

    # Save results
    save_json(results, output_path)
    print(f"Annotations saved to {output_path}")


if __name__ == "__main__":
    main()
