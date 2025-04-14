import json
import math
import os
import warnings
import sys
import subprocess
from typing import Dict, List, Set, Union, Optional, Any, Tuple

# Check if running in a virtual environment
in_venv = sys.prefix != sys.base_prefix
if not in_venv:
    print("IMPORTANT: This script requires the shapely and numpy packages.")
    print("Please run with: source .venv/bin/activate && python scripts/annotate_assignments.py")

# Attempt to import required packages
try:
    from shapely.geometry import shape, MultiPolygon, Polygon
    import shapely.ops
except ImportError:
    if in_venv:
        print("Installing required shapely package...")
        try:
            subprocess.check_call(["uv", "pip", "install", "shapely"])
        except:
            print("Failed to install shapely with uv. Trying with pip...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "shapely"])
    else:
        sys.exit("shapely package not found. Please activate the virtual environment first.")
    
    # Try import again after installation
    from shapely.geometry import shape, MultiPolygon, Polygon
    import shapely.ops

# Silence shapely warnings about oriented_envelope
warnings.filterwarnings("ignore", category=RuntimeWarning)

try:
    import numpy as np
except ImportError:
    if in_venv:
        print("Installing required numpy package...")
        try:
            subprocess.check_call(["uv", "pip", "install", "numpy"])
        except:
            print("Failed to install numpy with uv. Trying with pip...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"])
    else:
        sys.exit("numpy package not found. Please activate the virtual environment first.")
    
    # Try import again after installation
    import numpy as np

def load_json(filepath: str) -> Dict[str, Any]:
    with open(filepath, 'r') as f:
        return json.load(f)

def save_json(data: Dict[str, Any], filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
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

def is_enclave(constituency_districts: List[str], all_constituencies: Dict[str, List[str]], 
               adjacency_data: Dict[str, List[str]]) -> bool:
    """Check if a constituency is an enclave of another constituency."""
    if not constituency_districts:
        return False
    
    # Get all districts outside this constituency
    other_constituencies: Dict[str, List[str]] = {}
    for constituency, districts in all_constituencies.items():
        if set(districts) != set(constituency_districts):
            other_constituencies[constituency] = districts
    
    # Get all neighboring districts
    neighboring_districts: Set[str] = set()
    for district in constituency_districts:
        if district in adjacency_data:
            for adjacent in adjacency_data[district]:
                if adjacent not in constituency_districts:
                    neighboring_districts.add(adjacent)
    
    # If all neighboring districts belong to the same constituency, this is an enclave
    if not neighboring_districts:
        return False  # Isolated, not an enclave
    
    # Check if all neighboring districts are in the same constituency
    for constituency, districts in other_constituencies.items():
        if neighboring_districts.issubset(set(districts)):
            return True
    
    return False

def calculate_compactness(constituency_districts: List[str], geojson_data: Dict[str, Any]) -> Optional[float]:
    """Calculate compactness as area of shape over area of minimum bounding box."""
    # Extract geometries for the constituency districts
    constituency_features: List[Dict[str, Any]] = [f for f in geojson_data['features'] 
                           if f['properties']['name'] in constituency_districts]
    
    if not constituency_features:
        return None
    
    # Create a single geometry for the constituency
    try:
        geometries: List[Union[MultiPolygon, Polygon]] = [shape(feature['geometry']) for feature in constituency_features]
        constituency_geometry: Union[MultiPolygon, Polygon] = shapely.ops.unary_union(geometries)
        
        # Calculate area of the constituency
        constituency_area: float = constituency_geometry.area
        
        min_circle = shapely.minimum_bounding_circle(constituency_geometry)
        
        # Compactness ratio (0 to 1, higher is more compact)
        if min_circle and min_circle.area > 0:
            return constituency_area / min_circle.area
        else:
            return 0.0
    except Exception as e:
        print(f"Error calculating compactness for districts {constituency_districts}: {str(e)}")
        return 0.0

def main() -> None:
    # Load data
    assignment_data = load_json("assignments/official_ge_2025.json")
    adjacency_data = load_json("intermediate_data/ge2025_polling_districts_to_adjacent_districts.json")
    
    # Load GeoJSON data for compactness calculation
    with open("processed_data/ge2025_polling_districts_with_information.geojson", 'r') as f:
        geojson_data = json.load(f)
    
    # Create mapping of district name to elector size
    district_to_elector_size: Dict[str, int] = {}
    for feature in geojson_data['features']:
        district_name = feature['properties']['name']
        if 'elector_size' in feature['properties']:
            district_to_elector_size[district_name] = feature['properties']['elector_size']
    
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
        
        # Check if enclave
        is_enclave_result = is_enclave(polling_districts, constituencies, adjacency_data)
        
        # Calculate compactness
        compactness = calculate_compactness(polling_districts, geojson_data)
        
        # Calculate total elector size for the constituency
        total_elector_size = sum(district_to_elector_size.get(district, 0) for district in polling_districts)
        
        # Add to results
        results.append({
            "constituency_name": constituency_name,
            "member_size": item["member_size"],
            "elector_size": total_elector_size,
            "contiguous": contiguous,
            "is_enclave": is_enclave_result,
            "compactness": compactness
        })
    
    # Use the same name as the input file for output
    input_filename = os.path.basename("assignments/official_ge_2025.json")
    output_path = os.path.join("annotations", input_filename)
    
    # Save results
    save_json({"annotations": results}, output_path)
    print(f"Annotations saved to {output_path}")

if __name__ == "__main__":
    main()