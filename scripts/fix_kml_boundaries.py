# Use lxml for parsing and writing, plus refined manual post-processing
from lxml import etree as ET
import sys
from math import sqrt
from pathlib import Path
from collections import defaultdict
import re # Import regular expressions

# --- Configuration ---
INPUT_KML_FILE = Path("raw_data/ge2025_polling_districts.kml")
OUTPUT_KML_FILE = Path("processed_data/ge2025_polling_districts_fixed.kml")
SNAP_TOLERANCE = 1e-5  # Further increased tolerance for finding close vertices
INDENT_SPACES = "  " # Define the desired indent unit
MIN_AREA_THRESHOLD = 1e-7  # Minimum area for valid polygons
MIN_VERTICES = 4  # Minimum number of vertices for a valid polygon
# -------------------

def parse_coords(coord_string):
    """Parses the KML coordinate string into a list of (lon, lat, alt) tuples."""
    points = []
    lines = [line.strip() for line in coord_string.strip().split('\n') if line.strip()]
    for point_str in lines:
        try:
            lon, lat, alt = map(float, point_str.split(','))
            points.append((lon, lat, alt))
        except ValueError:
            if point_str: print(f"Warning: Skipping invalid coordinate point string: {point_str}")
            continue
    return points

def format_coord_tuple(lon, lat, alt):
    """Formats a single coordinate tuple with integer altitude and minimal precision."""
    alt_fmt = "{:d}".format(int(alt)) if alt == int(alt) else "{}".format(alt)
    lon_fmt = "{}".format(lon)
    lat_fmt = "{}".format(lat)
    return f"{lon_fmt},{lat_fmt},{alt_fmt}"

# --- Formatter using newlines ---
def format_coords_for_processing(coord_list):
    """Formats coordinates with one point per line, simple newline separation."""
    # Ensure there's a newline at the beginning and end for the post-processor
    coord_lines = [format_coord_tuple(lon, lat, alt) for lon, lat, alt in coord_list]
    return "\n" + "\n".join(coord_lines) + "\n"
# ---

def find_namespace(element):
    if element.nsmap and None in element.nsmap: return element.nsmap[None]
    if '}' in element.tag and element.tag.startswith('{'): return element.tag.split('}', 1)[0][1:]
    return ''

# --- DSU Functions (find_representative, union_sets, snap_vertices) ---
# (Remain unchanged)
def find_representative(vertex, parent_map):
    root = vertex
    while parent_map[root] != root: root = parent_map[root]
    curr = vertex
    while parent_map[curr] != root:
        next_v = parent_map[curr]; parent_map[curr] = root; curr = next_v
    return root

def union_sets(v1, v2, parent_map):
    root1 = find_representative(v1, parent_map)
    root2 = find_representative(v2, parent_map)
    if root1 != root2: parent_map[root2] = root1

def snap_vertices(placemarks_data, tolerance, max_passes=3):
    print("Starting multi-pass vertex snapping process...")
    
    original_placemarks = {k: list(v) for k, v in placemarks_data.items()}  # Make a deep copy
    total_merged_pairs = []
    total_merge_count = 0
    
    for pass_num in range(1, max_passes + 1):
        print(f"\nStarting pass {pass_num} of {max_passes}...")
        all_vertices_with_alt = {}
        all_coords_2d = set()
        vertex_to_district = {}  # Map vertices to districts that contain them
        
        print("Step 1: Collecting all unique vertices...")
        for district, coords_list in placemarks_data.items():
            for lon, lat, alt in coords_list:
                coord_2d = (lon, lat)
                all_coords_2d.add(coord_2d)
                if coord_2d not in all_vertices_with_alt:
                    all_vertices_with_alt[coord_2d] = alt
                
                # Track which districts contain this vertex
                if coord_2d not in vertex_to_district:
                    vertex_to_district[coord_2d] = set()
                vertex_to_district[coord_2d].add(district)
                
        unique_vertices_list = list(all_coords_2d)
        n_vertices = len(unique_vertices_list)
        print(f"Found {n_vertices} unique vertices.")
        
        parent = {v: v for v in unique_vertices_list}
        print(f"Step 2: Finding and merging vertices within tolerance ({tolerance:.1E} degrees)...")
        tolerance_sq = tolerance ** 2
        merge_count = 0
        merged_pairs = []  # Track which pairs were merged and their districts
        
        for i in range(n_vertices):
            v1 = unique_vertices_list[i]
            for j in range(i + 1, n_vertices):
                v2 = unique_vertices_list[j]
                dist_sq = (v1[0] - v2[0])**2 + (v1[1] - v2[1])**2
                if dist_sq < tolerance_sq:
                    if find_representative(v1, parent) != find_representative(v2, parent):
                        union_sets(v1, v2, parent)
                        merge_count += 1
                        
                        # Record the districts involved in this merge
                        districts1 = vertex_to_district.get(v1, set())
                        districts2 = vertex_to_district.get(v2, set())
                        involved_districts = districts1.union(districts2)
                        
                        if len(involved_districts) > 1:  # Only report if multiple districts are affected
                            merged_pairs.append({
                                'vertex1': v1,
                                'vertex2': v2,
                                'distance': dist_sq**0.5,
                                'districts': sorted(list(involved_districts))
                            })
        
        print(f"Merged {merge_count} pairs of close vertices in pass {pass_num}")
        total_merge_count += merge_count
        total_merged_pairs.extend(merged_pairs)
        
        if merge_count == 0:
            print(f"No more vertices to merge in pass {pass_num}. Early termination.")
            break
            
        # Update coordinates for the next pass
        print("Creating vertex mapping and updating placemarks...")
        vertex_snap_map = {}
        for v_orig in unique_vertices_list:
            representative = find_representative(v_orig, parent)
            vertex_snap_map[v_orig] = representative
        
        # Update the placemarks with snapped coordinates for the next pass
        for name, original_coords_list in placemarks_data.items():
            new_coords_list = [(vertex_snap_map.get((lon, lat), (lon, lat))[0],
                                vertex_snap_map.get((lon, lat), (lon, lat))[1],
                                alt)
                               for lon, lat, alt in original_coords_list]
            placemarks_data[name] = new_coords_list
    
    # Report the merged pairs between different districts
    if total_merged_pairs:
        print("\nBoundary alignments fixed between districts (all passes):")
        for idx, merge_info in enumerate(total_merged_pairs, 1):
            districts_str = ", ".join(merge_info['districts'])
            print(f"  {idx}. Districts: {districts_str}")
            print(f"     Coordinates: {merge_info['vertex1']} and {merge_info['vertex2']}")
            print(f"     Distance: {merge_info['distance']:.2e} degrees")
    
    print(f"\nVertex snapping finished. Total merged pairs: {total_merge_count}")
    
    # Final result is an updated placemarks_data and a map for the original vertices
    # Prepare final vertex map based on original coordinates
    final_vertex_map = {}
    representative_altitudes = {}
    
    # For each original vertex, find where it ended up after all passes
    for district, original_coords in original_placemarks.items():
        for i, (orig_lon, orig_lat, orig_alt) in enumerate(original_coords):
            orig_key = (orig_lon, orig_lat)
            if i < len(placemarks_data[district]):  # Safety check
                final_lon, final_lat, final_alt = placemarks_data[district][i]
                final_vertex_map[orig_key] = (final_lon, final_lat)
                if (final_lon, final_lat) not in representative_altitudes:
                    representative_altitudes[(final_lon, final_lat)] = final_alt
    
    return final_vertex_map, representative_altitudes
# --- End DSU Functions ---

# --- Refined Manual Indentation Function ---
def indent_coordinate_blocks(xml_string, indent_unit="  "):
    """
    Manually indents the lines within <coordinates> blocks
    relative to the <coordinates> tag itself. Assumes xml_string
    is generally pretty-printed for tags by lxml.
    """
    output_lines = []
    # Regex to find opening coordinates tag and capture its indent. Handles namespaces.
    open_tag_regex = re.compile(r"^(\s*)<(?:\w+:)?coordinates>")
    # Regex to find closing coordinates tag. Handles namespaces.
    close_tag_regex = re.compile(r"^\s*</(?:\w+:)?coordinates>")

    lines = xml_string.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        match_open = open_tag_regex.match(line)

        if match_open:
            # Found the opening <coordinates> tag
            base_indent = match_open.group(1)
            coord_indent = base_indent + indent_unit
            output_lines.append(line) # Add the opening tag line as is
            i += 1

            # For coordinate blocks, collect all content lines before processing
            content_lines = []
            while i < len(lines):
                inner_line = lines[i]
                if close_tag_regex.match(inner_line):
                    # Found closing tag - will process after collecting content
                    break
                content_lines.append(inner_line.strip())
                i += 1
            
            # Process all non-empty coordinate lines with proper indentation
            for content in content_lines:
                if content:
                    output_lines.append(coord_indent + content)
            
            # Add the closing tag with correct indentation
            if i < len(lines):
                output_lines.append(base_indent + "</coordinates>")
                i += 1
            else:
                print(f"Warning: Unterminated coordinates block detected near line: {line}")
        else:
            # Line is not the start of a coordinates block, add it as is
            output_lines.append(line)
            i += 1 # Move to next line

    # Add a final newline if the original string had one (splitlines removes it)
    final_string = "\n".join(output_lines)
    if xml_string.endswith('\n'):
        final_string += '\n'
    return final_string
# --- End Manual Indentation Function ---


# Function to identify weak boundaries with issues
def identify_weak_boundaries(placemarks_data):
    """Identify boundaries that have potential issues"""
    print("Checking for weak boundaries that need fixing...")
    weak_boundaries = {}
    
    for name, coords_list in placemarks_data.items():
        # Check for polygons with too few vertices
        if len(coords_list) < MIN_VERTICES:
            weak_boundaries[name] = f"Too few vertices (< {MIN_VERTICES})"
            continue
        
        # Check for self-intersections (simplified check)
        # This is just a basic check that could be expanded
        coord_set = set()
        has_duplicates = False
        duplicate_positions = []
        
        for i, (lon, lat, alt) in enumerate(coords_list[:-1]):  # Skip last point which should be same as first
            coord_2d = (lon, lat)
            if coord_2d in coord_set:
                has_duplicates = True
                duplicate_positions.append(i)
            coord_set.add(coord_2d)
        
        if has_duplicates:
            weak_boundaries[name] = f"Contains duplicate points at positions {duplicate_positions}"
        
        # Check for very small polygons (area too small)
        # Simple rectangular approximation for quick check
        lons = [p[0] for p in coords_list]
        lats = [p[1] for p in coords_list]
        area_approx = (max(lons) - min(lons)) * (max(lats) - min(lats))
        if area_approx < MIN_AREA_THRESHOLD:
            if name in weak_boundaries:
                weak_boundaries[name] += f", Very small area ({area_approx:.2e})"
            else:
                weak_boundaries[name] = f"Very small area ({area_approx:.2e})"
    
    if weak_boundaries:
        print(f"Found {len(weak_boundaries)} weak boundaries:")
        for name, issue in weak_boundaries.items():
            print(f"  - {name}: {issue}")
    else:
        print("No weak boundaries identified.")
    
    return weak_boundaries

# --- Main Script ---
if __name__ == "__main__":
    print(f"Processing KML file: {INPUT_KML_FILE} using lxml + manual indent")
    print(f"Python version: {sys.version}")

    if not INPUT_KML_FILE.is_file(): exit(f"Error: Input file not found at {INPUT_KML_FILE}")

    try:
        # --- Parsing with lxml (remove blank text helps pretty_print) ---
        # Keep remove_blank_text=True as it helps lxml's pretty printer
        parser = ET.XMLParser(remove_blank_text=True)
        tree = ET.parse(str(INPUT_KML_FILE), parser=parser)
        root = tree.getroot()

        namespace = find_namespace(root)
        print(f"Detected KML namespace: '{namespace}'")
        ns_map = {'kml': namespace} if namespace else {}

        placemarks_data = {}
        coords_elements_map = {}
        print("Extracting Placemark coordinates...")
        xpath_placemark = './/kml:Placemark' if namespace else './/Placemark'
        xpath_name = 'kml:name' if namespace else 'name'
        xpath_coords = 'kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates' if namespace else 'Polygon/outerBoundaryIs/LinearRing/coordinates'

        for placemark_elem in root.xpath(xpath_placemark, namespaces=ns_map):
            name_elem = placemark_elem.find(xpath_name, ns_map)
            coords_elem = placemark_elem.find(xpath_coords, ns_map)
            if name_elem is not None and name_elem.text is not None and \
               coords_elem is not None and coords_elem.text is not None:
                name = name_elem.text.strip()
                coords_list = parse_coords(coords_elem.text)
                if coords_list:
                    if len(coords_list) < 2 or coords_list[0] != coords_list[-1]:
                        if len(coords_list) >= 1: 
                            print(f"Fixing unclosed polygon for {name} by adding closing point")
                            coords_list.append(coords_list[0])
                        else: continue
                    placemarks_data[name] = coords_list
                    # Store the element itself for later modification
                    coords_elements_map[name] = coords_elem

        print(f"Extracted valid coordinate data for {len(placemarks_data)} Placemarks.")
        if not placemarks_data: exit("Error: No valid Placemark data found.")
        
        # Identify weak boundaries before snapping
        weak_boundaries = identify_weak_boundaries(placemarks_data)

        # Do multiple passes of vertex snapping to ensure all boundaries are aligned
        vertex_snap_map, representative_altitudes = snap_vertices(placemarks_data, SNAP_TOLERANCE, max_passes=3)

        # The placemarks_data is now updated with the snapped coordinates from multiple passes
        print("Rebuilding Placemarks with snapped coordinates...")
        update_count = 0
        
        # Final check for fully aligned boundaries - verify no remaining close pairs
        district_boundaries = {}
        
        # Extract boundary points for each district
        for name, coords_list in placemarks_data.items():
            district_boundaries[name] = set((lon, lat) for lon, lat, _ in coords_list)
        
        # Check for any remaining close but unaligned boundaries
        remaining_misalignments = []
        print("\nVerifying final boundary alignments...")
        
        for d1, points1 in district_boundaries.items():
            for d2, points2 in district_boundaries.items():
                if d1 >= d2:  # Only check each pair once
                    continue
                    
                # Check if any points are very close but not identical
                for p1 in points1:
                    for p2 in points2:
                        if p1 == p2:  # Points are exactly aligned
                            continue
                            
                        dist_sq = (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
                        if dist_sq < (SNAP_TOLERANCE/10)**2:  # Use tighter tolerance for verification
                            remaining_misalignments.append({
                                'district1': d1,
                                'district2': d2,
                                'point1': p1,
                                'point2': p2,
                                'distance': dist_sq**0.5
                            })
        
        if remaining_misalignments:
            print(f"WARNING: Found {len(remaining_misalignments)} remaining potential misalignments after snapping")
            for i, misalign in enumerate(remaining_misalignments[:10], 1):  # Show at most 10
                print(f"  {i}. Between {misalign['district1']} and {misalign['district2']}")
                print(f"     Points: {misalign['point1']} and {misalign['point2']}")
                print(f"     Distance: {misalign['distance']:.2e} degrees")
            if len(remaining_misalignments) > 10:
                print(f"     ... and {len(remaining_misalignments) - 10} more")
        else:
            print("All boundaries are perfectly aligned!")
            
        # Update XML with snapped coordinates
        for name, original_coords_list in placemarks_data.items():
            # Format coordinates with newlines (including leading/trailing for structure)
            coord_lines_str = format_coords_for_processing(original_coords_list)

            coords_elem = coords_elements_map.get(name)
            if coords_elem is not None:
                 # Assign the simple newline-separated string.
                 # lxml's pretty_print will handle base indent, manual step fixes inner.
                 coords_elem.text = coord_lines_str
                 update_count += 1
            else:
                 print(f"Error: Could not find stored coordinates element for '{name}' during update.")

        print(f"Updated coordinates for {update_count} Placemarks.")

        # --- Generate pretty-printed XML string using lxml ---
        print("Generating base pretty-printed XML string...")
        pretty_xml_bytes = ET.tostring(tree,
                                       encoding='UTF-8',
                                       xml_declaration=True,
                                       pretty_print=True) # Use lxml's pretty print
        pretty_xml_string = pretty_xml_bytes.decode('utf-8')

        # --- Apply manual indentation to coordinate blocks ---
        print("Applying manual indentation to <coordinates> blocks...")
        final_xml_string = indent_coordinate_blocks(pretty_xml_string, indent_unit=INDENT_SPACES)

        # --- Write the final, manually adjusted string to file ---
        print(f"Writing final fixed KML to: {OUTPUT_KML_FILE}")
        OUTPUT_KML_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_KML_FILE, 'w', encoding='utf-8') as f:
            f.write(final_xml_string)

        if weak_boundaries:
            print(f"Fixed {len(weak_boundaries)} weak boundaries.")
        print("Processing complete.")

    except ET.XMLSyntaxError as e: print(f"Error parsing KML file with lxml: {e}")
    except FileNotFoundError: print(f"Error: Input file not found at {INPUT_KML_FILE}")
    except ImportError:
        print("\nError: This script requires the 'lxml' library.")
        print("Please install it using: pip install lxml")
        exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()