import xml.etree.ElementTree as ET
from math import sqrt
from pathlib import Path
from collections import defaultdict

# --- Configuration ---
INPUT_KML_FILE = Path("raw_data/ge2025_polling_districts.kml")
OUTPUT_KML_FILE = Path("processed_data/ge2025_polling_districts_fixed.kml")
SNAP_TOLERANCE = 1e-9 # Adjust carefully if needed
# -------------------

def parse_coords(coord_string):
    """Parses the KML coordinate string into a list of (lon, lat, alt) tuples."""
    points = []
    for point_str in coord_string.strip().split():
        try:
            lon, lat, alt = map(float, point_str.split(','))
            points.append((lon, lat, alt))
        except ValueError:
            print(f"Warning: Skipping invalid coordinate point string: {point_str}")
            continue
    return points

def format_coords(coord_list):
    """Formats a list of (lon, lat, alt) tuples back into a KML coordinate string."""
    return "\n".join(f"{lon:.8f},{lat:.8f},{alt}" for lon, lat, alt in coord_list)

# --- Updated find_namespace function ---
def find_namespace(element):
    """Extracts the namespace URI from an element's tag string."""
    tag = element.tag
    # Namespaced tags are usually in the format {namespace_uri}local_name
    if '}' in tag and tag.startswith('{'):
        namespace_uri = tag.split('}', 1)[0][1:] # Extract the part within {}
        return namespace_uri
    else:
        # The element tag doesn't seem to be in the expected namespaced format
        # This might happen for comments or processing instructions, or if no namespace is defined
        return ''
# --- End of updated function ---

def find_representative(vertex, parent_map):
    """Finds the root representative of a vertex in a Disjoint Set Union."""
    root = vertex
    while parent_map[root] != root:
        root = parent_map[root]
    # Path compression
    curr = vertex
    while parent_map[curr] != root:
        next_v = parent_map[curr]
        parent_map[curr] = root
        curr = next_v
    return root

def union_sets(v1, v2, parent_map):
    """Merges the sets containing v1 and v2."""
    root1 = find_representative(v1, parent_map)
    root2 = find_representative(v2, parent_map)
    if root1 != root2:
        parent_map[root2] = root1

def snap_vertices(placemarks_data, tolerance):
    """
    Identifies close vertices across all placemarks and creates a map
    from original vertices to snapped vertices using Disjoint Set Union.
    """
    print("Starting vertex snapping process...")
    all_vertices_with_alt = {}
    all_coords_2d = set()

    print("Step 1: Collecting all unique vertices...")
    for name, coords_list in placemarks_data.items():
        for lon, lat, alt in coords_list:
            coord_2d = (lon, lat)
            all_coords_2d.add(coord_2d)
            if coord_2d not in all_vertices_with_alt:
                all_vertices_with_alt[coord_2d] = alt

    unique_vertices_list = list(all_coords_2d)
    n_vertices = len(unique_vertices_list)
    print(f"Found {n_vertices} unique vertices.")

    parent = {v: v for v in unique_vertices_list}

    print(f"Step 2: Finding and merging vertices within tolerance ({tolerance:.1E} degrees)...")
    tolerance_sq = tolerance ** 2
    merge_count = 0
    for i in range(n_vertices):
        v1 = unique_vertices_list[i]
        if i % 1000 == 0 and i > 0:
            print(f"  Processed {i}/{n_vertices} vertices...")

        for j in range(i + 1, n_vertices):
            v2 = unique_vertices_list[j]
            dist_sq = (v1[0] - v2[0])**2 + (v1[1] - v2[1])**2
            if dist_sq < tolerance_sq:
                if find_representative(v1, parent) != find_representative(v2, parent):
                    union_sets(v1, v2, parent)
                    merge_count += 1

    print(f"Merged {merge_count} pairs of close vertices into groups.")

    print("Step 3: Creating final map from original vertex to representative vertex...")
    vertex_snap_map = {}
    representative_altitudes = {}
    for v_orig in unique_vertices_list:
        representative = find_representative(v_orig, parent)
        vertex_snap_map[v_orig] = representative
        if representative not in representative_altitudes:
            representative_altitudes[representative] = all_vertices_with_alt[representative]

    print("Vertex snapping finished.")
    return vertex_snap_map, representative_altitudes

# --- Main Script ---
if __name__ == "__main__":
    # Use the script name provided in the error message if it's different
    script_path = Path(__file__) # Assumes the script is run directly
    # Or hardcode if necessary: script_path = Path("scripts/fix_kml_boundaries.py")

    print(f"Processing KML file: {INPUT_KML_FILE}")

    if not INPUT_KML_FILE.is_file():
        print(f"Error: Input file not found at {INPUT_KML_FILE}")
        exit(1)

    try:
        tree = ET.parse(INPUT_KML_FILE)
        root = tree.getroot()

        # Use the updated find_namespace function
        namespace = find_namespace(root)
        print(f"Detected KML namespace: '{namespace}'") # Added print statement for verification

        ns_map = {'kml': namespace} if namespace else {}
        if namespace:
            ET.register_namespace('', namespace) # Register for output serialization

        placemarks_data = {}
        placemark_elements = {}

        print("Extracting Placemark coordinates...")
        xpath_placemark = './/kml:Placemark' if namespace else './/Placemark'
        xpath_name = 'kml:name' if namespace else 'name'
        xpath_coords = './/kml:coordinates' if namespace else './/coordinates'

        # Ensure we search from the root element
        for placemark_elem in root.findall(xpath_placemark, ns_map):
            name_elem = placemark_elem.find(xpath_name, ns_map)
            coords_elem = placemark_elem.find(xpath_coords, ns_map) # Search within placemark

            if name_elem is not None and coords_elem is not None and coords_elem.text:
                name = name_elem.text.strip()
                coords_list = parse_coords(coords_elem.text)
                if coords_list:
                    if coords_list[0] != coords_list[-1]:
                        print(f"Warning: Polygon '{name}' was not closed. Closing it.")
                        coords_list.append(coords_list[0])
                    placemarks_data[name] = coords_list
                    placemark_elements[name] = placemark_elem
                else:
                    print(f"Warning: No valid coordinates found for Placemark '{name}'")
            #else: # Reduce noise, only print if essential info is missing
            #    print("Warning: Found Placemark potentially missing name or coordinates, skipping.")


        if not placemarks_data:
            print("Error: No valid Placemark data found in the KML file.")
            exit(1)

        print(f"Extracted data for {len(placemarks_data)} Placemarks.")

        vertex_snap_map, representative_altitudes = snap_vertices(placemarks_data, SNAP_TOLERANCE)

        print("Rebuilding Placemarks with snapped coordinates...")
        for name, original_coords_list in placemarks_data.items():
            new_coords_list = []
            for lon, lat, alt_original in original_coords_list:
                original_2d = (lon, lat)
                snapped_2d = vertex_snap_map.get(original_2d)

                if snapped_2d:
                    new_coords_list.append((snapped_2d[0], snapped_2d[1], alt_original))
                else:
                    print(f"Warning: Vertex ({lon},{lat}) not found in snap map for Placemark '{name}'. Using original.")
                    new_coords_list.append((lon, lat, alt_original))

            new_coords_str = format_coords(new_coords_list)

            placemark_elem = placemark_elements.get(name)
            if placemark_elem:
                 # Search for coordinates *within* this specific placemark element
                 coords_elem = placemark_elem.find(xpath_coords, ns_map)
                 if coords_elem is not None:
                     coords_elem.text = "\n" + new_coords_str + "\n"
                 else:
                     # This might indicate a structure issue, e.g., MultiGeometry instead of Polygon
                     print(f"Error: Could not find coordinates element within Placemark '{name}' during update. Structure might be unexpected.")
            else:
                print(f"Error: Could not find Placemark element for '{name}' during update.")


        print(f"Writing fixed KML to: {OUTPUT_KML_FILE}")
        OUTPUT_KML_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Important: Use the registered namespace prefix when writing
        tree.write(OUTPUT_KML_FILE, encoding='UTF-8', xml_declaration=True)

        print("Processing complete.")

    except ET.ParseError as e:
        print(f"Error parsing KML file: {e}")
    except FileNotFoundError:
        print(f"Error: Input file not found at {INPUT_KML_FILE}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()