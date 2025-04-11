#!/usr/bin/env python3

import xml.etree.ElementTree as ET
from shapely.geometry import Polygon, LineString, Point
import json
import os
import numpy as np
import networkx as nx

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
    
    # Compute bounding boxes for quick filtering
    bounding_boxes = {}
    for district_id, polygon in districts.items():
        bounding_boxes[district_id] = polygon.bounds  # (minx, miny, maxx, maxy)
    
    # Check each pair of districts with spatial optimization
    district_ids = list(districts.keys())
    total_pairs = len(district_ids) * (len(district_ids) - 1) // 2
    processed = 0
    skipped = 0
    
    print(f"Processing {total_pairs} district pairs with spatial optimization...")
    
    # Define a distance threshold - if bounding boxes are farther apart than this, skip the check
    # Tuned based on Singapore's geography - adjust as needed for your specific context
    distance_threshold = 0.01  # in coordinate units (degrees)
    
    for i in range(len(district_ids)):
        for j in range(i+1, len(district_ids)):
            id_a = district_ids[i]
            id_b = district_ids[j]
            
            processed += 1
            if processed % 10000 == 0:
                print(f"Processed {processed}/{total_pairs} pairs ({processed/total_pairs*100:.1f}%), skipped {skipped} distant pairs")
            
            # Quick check using bounding boxes before more expensive operations
            bbox_a = bounding_boxes[id_a]
            bbox_b = bounding_boxes[id_b]
            
            # If bounding boxes are far apart, skip the detailed check
            if (bbox_a[2] < bbox_b[0] - distance_threshold or  # A's max x < B's min x
                bbox_b[2] < bbox_a[0] - distance_threshold or  # B's max x < A's min x
                bbox_a[3] < bbox_b[1] - distance_threshold or  # A's max y < B's min y
                bbox_b[3] < bbox_a[1] - distance_threshold):   # B's max y < A's min y
                skipped += 1
                continue
            
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
    
    print(f"Optimization summary: Skipped {skipped} pairs out of {total_pairs} ({skipped/total_pairs*100:.1f}%) due to distance filtering")
    return adjacency

def detect_quadpoints(districts, adjacency):
    """
    Detect quadpoints (where 4 or more districts meet at a point)
    and identify non-planar edges between them
    """
    # Create a graph from the adjacency list
    G = nx.Graph()
    for district, neighbors in adjacency.items():
        for neighbor in neighbors:
            G.add_edge(district, neighbor)
    
    # Find all vertices in the graph (points where polygons meet)
    # Using a spatial index to optimize
    from collections import defaultdict
    vertices = defaultdict(list)  # {(x, y): [district_ids]}
    
    print("Building spatial index of boundary points...")
    
    # Store all distinct coordinates with their precision reduced to handle floating point issues
    precision = 6  # Number of decimal places to keep
    
    # For each district, get its boundary points
    for district_id, polygon in districts.items():
        # Get exterior boundary points
        boundary = polygon.exterior.coords
        for point in boundary:
            # Round to handle floating point precision issues
            rounded_point = (round(point[0], precision), round(point[1], precision))
            if district_id not in vertices[rounded_point]:
                vertices[rounded_point].append(district_id)
    
    # Find quadpoints (points where 4 or more districts meet)
    quadpoints = {point: districts_list for point, districts_list in vertices.items() 
                  if len(districts_list) >= 4}
    print(f"Found {len(quadpoints)} potential quadpoints")
    
    # For each quadpoint, identify diagonal pairs of districts that
    # might have false adjacency
    edges_to_remove = []
    processed_quadpoints = 0
    
    for point, districts_at_point in quadpoints.items():
        processed_quadpoints += 1
        if processed_quadpoints % 20 == 0:
            print(f"Processed {processed_quadpoints}/{len(quadpoints)} quadpoints")
            
        if len(districts_at_point) > 10:  # Skip if too many districts at this point
            continue
            
        # Create a point object
        quad_point = Point(point)
        
        # For each district at this point, calculate the angles of its vertices
        district_angles = {}
        
        # Vector calculation is expensive, so we'll use a faster approximation 
        # to determine the angular position of each district around the quadpoint
        for district_id in districts_at_point:
            polygon = districts[district_id]
            
            # Use the centroid as a proxy for determining the district's position
            # relative to the quadpoint - this is faster than calculating angles
            centroid = polygon.centroid
            
            # Calculate vector from quadpoint to centroid
            vector = (centroid.x - point[0], centroid.y - point[1])
            
            # Calculate angle
            angle = np.arctan2(vector[1], vector[0])
            if angle < 0:
                angle += 2 * np.pi
                
            district_angles[district_id] = angle
        
        # Sort districts by angle around the quadpoint
        sorted_districts = sorted(district_angles.keys(), key=lambda d: district_angles[d])
        
        # Check if non-adjacent districts in the circular order are connected
        # in the adjacency graph, which would create a non-planar edge
        # Only check opposite districts
        districts_count = len(sorted_districts)
        for i in range(districts_count // 2):
            # Get districts that are opposite in the circular order
            opposite_idx = (i + districts_count // 2) % districts_count
            district_a = sorted_districts[i]
            district_b = sorted_districts[opposite_idx]
            
            # If they're connected but shouldn't be (opposite sides of quadpoint)
            if district_b in adjacency.get(district_a, []):
                edges_to_remove.append((district_a, district_b))
    
    return edges_to_remove

def remove_non_planar_edges(adjacency, edges_to_remove):
    """Remove non-planar edges from the adjacency list"""
    modified_adjacency = {k: list(v) for k, v in adjacency.items()}  # Deep copy
    
    for district_a, district_b in edges_to_remove:
        if district_b in modified_adjacency[district_a]:
            modified_adjacency[district_a].remove(district_b)
        if district_a in modified_adjacency[district_b]:
            modified_adjacency[district_b].remove(district_a)
    
    return modified_adjacency

def planarize_graph_iteratively(adjacency, max_iterations=500, protected_pairs=None):
    """
    Iteratively remove edges from the graph based on degree and shortest path criteria
    until the graph is planar.
    
    Parameters:
    - adjacency: The adjacency list to planarize
    - max_iterations: Maximum number of iterations to perform
    - protected_pairs: List of district pairs (tuples) whose adjacency should be preserved
    """
    modified_adjacency = {k: list(v) for k, v in adjacency.items()}  # Deep copy
    
    # Ensure protected_pairs is a list
    if protected_pairs is None:
        protected_pairs = []
    
    # Normalize the protected pairs (ensure order doesn't matter)
    normalized_protected_pairs = []
    for a, b in protected_pairs:
        if a > b:
            normalized_protected_pairs.append((b, a))
        else:
            normalized_protected_pairs.append((a, b))
    
    print(f"Protected adjacency pairs: {normalized_protected_pairs}")
    
    # Keep track of removed edges for reporting
    all_removed_edges = []
    
    # Create a graph from the adjacency list
    G = nx.Graph()
    for district, neighbors in modified_adjacency.items():
        for neighbor in neighbors:
            G.add_edge(district, neighbor)
    
    print(f"Starting iterative planarization with max {max_iterations} iterations")
    print(f"Initial graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Get high-degree nodes - only compute once to save memory
    node_degrees = sorted(G.degree(), key=lambda x: x[1], reverse=True)
    high_degree_nodes = [node for node, degree in node_degrees if degree > 10]
    print(f"Found {len(high_degree_nodes)} high-degree nodes (degree > 10)")
    
    # Save original high-degree node pairs to prioritize in removal
    high_degree_pairs = []
    for i in range(len(high_degree_nodes)):
        for j in range(i+1, len(high_degree_nodes)):
            node_a = high_degree_nodes[i]
            node_b = high_degree_nodes[j]
            if G.has_edge(node_a, node_b):
                high_degree_pairs.append((node_a, node_b))
    
    if high_degree_pairs:
        print(f"Found {len(high_degree_pairs)} connections between high-degree nodes to prioritize")
    
    # Try to make the graph planar by removing edges between high-degree nodes
    iterations = 0
    check_planarity_every = 5  # Check planarity every N iterations to save computation
    is_planar = False
    
    while iterations < max_iterations and not is_planar:
        # Check planarity periodically to save computation
        if iterations % check_planarity_every == 0 or iterations >= max_iterations - 5:
            is_planar, _, kuratowski_subgraphs = verify_planarity(modified_adjacency)
            if is_planar:
                print(f"Graph is now planar after {iterations} iterations")
                break
            elif iterations % 50 == 0:  # Print non-planar examples periodically
                # Print first non-planar subgraph as example
                try:
                    if kuratowski_subgraphs and hasattr(kuratowski_subgraphs, '__iter__'):
                        # For list-like objects
                        if hasattr(kuratowski_subgraphs, '__len__') and len(kuratowski_subgraphs) > 0:
                            first_subgraph = kuratowski_subgraphs[0]
                            nodes = list(first_subgraph.nodes())
                            print(f"\nPersistent non-planar subgraph after {iterations} iterations:")
                            print(f"  Nodes: {', '.join(sorted(nodes[:10]))} {'...' if len(nodes) > 10 else ''}")
                            print(f"  Total edges: {first_subgraph.number_of_edges()}")
                        # For generator-like objects
                        elif isinstance(kuratowski_subgraphs, (iter, map, filter)) or hasattr(kuratowski_subgraphs, 'next') or hasattr(kuratowski_subgraphs, '__next__'):
                            try:
                                first_subgraph = next(kuratowski_subgraphs)
                                nodes = list(first_subgraph.nodes())
                                print(f"\nPersistent non-planar subgraph after {iterations} iterations:")
                                print(f"  Nodes: {', '.join(sorted(nodes[:10]))} {'...' if len(nodes) > 10 else ''}")
                                print(f"  Total edges: {first_subgraph.number_of_edges()}")
                            except StopIteration:
                                print(f"\nNo more non-planar subgraphs available")
                except Exception as e:
                    print(f"Error examining non-planar subgraph: {e}")
        
        # Update graph more efficiently - only rebuild when needed
        if iterations % 10 == 0:  # Rebuild graph periodically
            G = nx.Graph()
            for district, neighbors in modified_adjacency.items():
                for neighbor in neighbors:
                    G.add_edge(district, neighbor)
        
        # Every 25 iterations, try to use a more direct approach to planarization using Boyer-Myrvold
        # algorithm's output for guidance
        if iterations % 25 == 0 and iterations > 0:
            # Try to identify problematic edges using a planar layout attempt
            try:
                # Use Boyer-Myrvold algorithm to find planar embedding or identify problems
                # By checking a small random subset of the graph first
                sampled_nodes = list(G.nodes())
                # Create a subgraph with fewer nodes to handle large graphs
                sample_size = min(400, len(sampled_nodes))
                sampled_nodes = sampled_nodes[:sample_size]
                subgraph = G.subgraph(sampled_nodes)
                
                # Find edges with highest betweenness centrality to prioritize removal
                edge_betweenness = nx.edge_betweenness_centrality(subgraph)
                high_betweenness_edges = sorted(edge_betweenness.items(), key=lambda x: x[1], reverse=True)[:20]
                
                # Check if any of these edges exist in the main graph
                for edge, _ in high_betweenness_edges:
                    if G.has_edge(edge[0], edge[1]):
                        edge_to_remove = edge
                        print(f"Found high betweenness edge to remove: {edge_to_remove}")
                        break
                else:
                    edge_to_remove = None
            except Exception as e:
                print(f"Error in planarization algorithm: {e}")
                edge_to_remove = None
        # For most iterations, use simpler heuristics
        else:
            # Strategy 1: Remove edges between the highest degree nodes
            if iterations < 100:
                # Get the highest degree nodes
                node_degrees = sorted(G.degree(), key=lambda x: x[1], reverse=True)
                high_degree_nodes = [node for node, degree in node_degrees[:30] if degree > 6]
                
                edge_to_remove = None
                # Find edges between high-degree nodes
                for i in range(len(high_degree_nodes)):
                    for j in range(i+1, len(high_degree_nodes)):
                        node_a = high_degree_nodes[i]
                        node_b = high_degree_nodes[j]
                        if G.has_edge(node_a, node_b):
                            edge_to_remove = (node_a, node_b)
                            break
                    if edge_to_remove:
                        break
            
            # Strategy 2: Find cycles and remove high-degree edges from them
            if (iterations >= 100 or not edge_to_remove) and iterations % 2 == 0:
                # Try to find a cycle and remove an edge from it
                try:
                    cycles = nx.cycle_basis(G)
                    if cycles:
                        # Find the largest cycle
                        largest_cycle = max(cycles, key=len)
                        # Create edges from the cycle
                        cycle_edges = []
                        for i in range(len(largest_cycle)):
                            u = largest_cycle[i]
                            v = largest_cycle[(i + 1) % len(largest_cycle)]
                            if G.has_edge(u, v):
                                cycle_edges.append((u, v))
                        
                        # Choose the edge with the highest degree sum
                        if cycle_edges:
                            edge_to_remove = max(cycle_edges, key=lambda x: G.degree(x[0]) + G.degree(x[1]))
                except Exception as e:
                    print(f"Error finding cycle: {e}")
                    edge_to_remove = None
            
            # Strategy 3: Find edges between nodes with high node betweenness
            if (iterations >= 100 or not edge_to_remove) and iterations % 3 == 0:
                try:
                    # Calculate node betweenness (only for a sample of nodes to save time)
                    betweenness = nx.betweenness_centrality(G, k=min(100, G.number_of_nodes()))
                    # Sort nodes by betweenness
                    high_betweenness_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:20]
                    high_betweenness_nodes = [n for n, b in high_betweenness_nodes]
                    
                    # Find edges between high-betweenness nodes
                    for i in range(len(high_betweenness_nodes)):
                        for j in range(i+1, len(high_betweenness_nodes)):
                            node_a = high_betweenness_nodes[i]
                            node_b = high_betweenness_nodes[j]
                            if G.has_edge(node_a, node_b):
                                edge_to_remove = (node_a, node_b)
                                break
                        if edge_to_remove:
                            break
                except Exception as e:
                    print(f"Error calculating betweenness: {e}")
                    edge_to_remove = None
            
            # Strategy 4: Last resort, find any edge between nodes with degree > 3
            if not edge_to_remove:
                candidates = [(u, v) for u, v in G.edges() if G.degree(u) > 3 and G.degree(v) > 3]
                if candidates:
                    # Take one with highest degree sum
                    edge_to_remove = max(candidates, key=lambda x: G.degree(x[0]) + G.degree(x[1]))
                else:
                    # If all else fails, take any edge
                    candidates = list(G.edges())
                    if candidates:
                        edge_to_remove = candidates[0]
                    else:
                        edge_to_remove = None
        
        if not edge_to_remove:
            print(f"No suitable edge found to remove in iteration {iterations}")
            break
        
        u, v = edge_to_remove
        
        # Check if this edge is protected
        normalized_edge = (u, v) if u < v else (v, u)
        if normalized_edge in normalized_protected_pairs:
            print(f"Skipping protected edge {u} -- {v}")
            
            # To avoid infinite loops, we'll examine other edges for removal
            # Let's remove another edge that's not protected
            iterations += 1
            
            # Find an alternative edge
            found_alternative = False
            for non_protected_edge in G.edges():
                alt_u, alt_v = non_protected_edge
                alt_norm = (alt_u, alt_v) if alt_u < alt_v else (alt_v, alt_u)
                
                # Skip if this is a protected edge
                if alt_norm in normalized_protected_pairs:
                    continue
                
                # Found an unprotected edge to remove
                u, v = alt_u, alt_v
                print(f"Found alternative edge to remove: {u} -- {v}")
                found_alternative = True
                break
                
            # If no alternative found, cannot proceed with planarization
            if not found_alternative:
                print("No alternative edges found for removal - cannot proceed with planarization")
                return modified_adjacency, all_removed_edges
            
            # If we found an alternative, continue with normal processing (no continue or break needed)
        
        # Remove the edge from our adjacency list
        if v in modified_adjacency.get(u, []):
            modified_adjacency[u].remove(v)
        if u in modified_adjacency.get(v, []):
            modified_adjacency[v].remove(u)
        
        # Also remove from the graph to avoid rebuilding
        if G.has_edge(u, v):
            G.remove_edge(u, v)
        
        all_removed_edges.append((u, v))
        print(f"Iteration {iterations+1}: Removed edge {u} -- {v}")
        
        # Only check planarity occasionally to save computation
        if (iterations + 1) % check_planarity_every == 0:
            is_planar, _, _ = verify_planarity(modified_adjacency)
            if is_planar:
                print(f"Graph is now planar after removing edge {u} -- {v}")
                break
        
        iterations += 1
        
        # Batch reporting for progress
        if iterations % 50 == 0:
            print(f"Completed {iterations} iterations, removed {len(all_removed_edges)} edges so far")
    
    # Final check
    is_planar, _, _ = verify_planarity(modified_adjacency)
    print(f"Final graph is {'planar' if is_planar else 'still not planar'} after {iterations} iterations")
    
    # If not planar after all our efforts, force planarization
    if not is_planar:
        print("Applying force planarization via maximally planar subgraph...")
        
        # Create a graph from our current adjacency
        G = nx.Graph()
        for district, neighbors in modified_adjacency.items():
            for neighbor in neighbors:
                G.add_edge(district, neighbor)
        
        # Apply a planar layout algorithm that can force planarization
        # First attempt using best-first planar embedding
        try:
            # Extract maximum planar subgraph using networkx community detection
            # Start by identifying communities
            communities = list(nx.algorithms.community.greedy_modularity_communities(G))
            print(f"Identified {len(communities)} communities in the graph")
            
            # For each community, try to make it planar
            removed_edges = 0
            for i, community in enumerate(communities):
                subgraph = G.subgraph(community)
                print(f"Processing community {i+1}/{len(communities)} with {len(community)} nodes")
                
                # Get the subgraph adjacency for this community
                community_adjacency = {n: [m for m in modified_adjacency.get(n, []) if m in community] 
                                      for n in community if n in modified_adjacency}
                
                # Try to make each community planar
                planarization_attempts = 0
                max_attempts = 30  # Limit attempts per community
                    
                while planarization_attempts < max_attempts:
                    is_sg_planar, _, kuratowski = verify_planarity(community_adjacency, 
                                                                verbose=(planarization_attempts == 0))
                    if is_sg_planar:
                        break
                    
                    # If we have Kuratowski subgraphs, remove an edge from one
                    if kuratowski:
                        try:
                            # Use the Kuratowski subgraph to identify a problematic edge
                            first_subgraph = next(kuratowski)
                            
                            # Choose edge with highest degree sum
                            edge_scores = {}
                            for u, v in first_subgraph.edges():
                                # Calculate score - prefer edges that connect high-degree nodes
                                deg_u = len(community_adjacency.get(u, []))
                                deg_v = len(community_adjacency.get(v, []))
                                edge_scores[(u, v)] = deg_u + deg_v
                            
                            if edge_scores:
                                edge_to_remove = max(edge_scores.items(), key=lambda x: x[1])[0]
                                u, v = edge_to_remove
                                
                                # Remove from the community adjacency
                                if v in community_adjacency.get(u, []):
                                    community_adjacency[u].remove(v)
                                if u in community_adjacency.get(v, []):
                                    community_adjacency[v].remove(u)
                                
                                # Also remove from the full adjacency
                                if v in modified_adjacency.get(u, []):
                                    modified_adjacency[u].remove(v)
                                if u in modified_adjacency.get(v, []):
                                    modified_adjacency[v].remove(u)
                                    
                                removed_edges += 1
                                
                                if planarization_attempts == 0:
                                    print(f"  Removing edge {u} -- {v} from non-planar subgraph")
                            else:
                                print(f"  No edges found in Kuratowski subgraph for community {i+1}")
                                break
                        except Exception as e:
                            print(f"  Error in Kuratowski-based removal: {e}")
                            break
                    else:
                        # Fallback - just find any high-degree edge
                        edge_to_remove = None
                        for n1 in community:
                            if n1 not in community_adjacency:
                                continue
                            for n2 in list(community_adjacency.get(n1, [])):
                                deg_sum = len(community_adjacency.get(n1, [])) + len(community_adjacency.get(n2, []))
                                if deg_sum > 4:
                                    edge_to_remove = (n1, n2)
                                    break
                            if edge_to_remove:
                                break
                        
                        # If no suitable edge found, just break
                        if not edge_to_remove:
                            print(f"  Could not planarize community {i+1}")
                            break
                        
                        # Remove the edge
                        u, v = edge_to_remove
                        if v in community_adjacency.get(u, []):
                            community_adjacency[u].remove(v)
                        if u in community_adjacency.get(v, []):
                            community_adjacency[v].remove(u)
                            
                        # Also remove from full adjacency
                        if v in modified_adjacency.get(u, []):
                            modified_adjacency[u].remove(v)
                        if u in modified_adjacency.get(v, []):
                            modified_adjacency[v].remove(u)
                            
                        removed_edges += 1
                    
                    planarization_attempts += 1
                    
                    # Break out if we're removing too many edges
                    if removed_edges > 1000:
                        print("Removing too many edges, stopping planarization")
                        break
                
                # Report if couldn't planarize
                if not is_sg_planar:
                    print(f"  Warning: Community {i+1} is still not planar after {planarization_attempts} attempts")
                elif planarization_attempts > 0:
                    print(f"  Successfully planarized community {i+1} after removing {planarization_attempts} edges")
            
            print(f"Removed {removed_edges} additional edges during forced planarization")
            
            # Final check
            is_planar, _, _ = verify_planarity(modified_adjacency)
            print(f"After force planarization, graph is {'planar' if is_planar else 'STILL NOT planar!!!'}")
            
            # If still not planar, we'll just report that
            if not is_planar:
                print("WARNING: Could not achieve planarity after all attempts")
        
        except Exception as e:
            print(f"Error during force planarization: {e}")
    
    # Check if any district has become disconnected
    isolated = [d for d, adj in modified_adjacency.items() if len(adj) == 0]
    if isolated:
        print(f"Warning: {len(isolated)} districts have no adjacencies after planarization")
        
        # Try to reconnect isolated districts to their original neighbors if possible
        print("Attempting to reconnect isolated districts...")
        for district in isolated:
            if district in adjacency:  # Get original adjacencies
                original_neighbors = adjacency[district]
                # Try to connect to at least one neighbor, prioritizing those with fewer connections
                if original_neighbors:
                    best_neighbor = min(original_neighbors, key=lambda n: len(modified_adjacency.get(n, [])) if n in modified_adjacency else 0)
                    print(f"Reconnecting {district} to {best_neighbor}")
                    
                    # Add the edge back
                    if district not in modified_adjacency:
                        modified_adjacency[district] = []
                    if best_neighbor not in modified_adjacency:
                        modified_adjacency[best_neighbor] = []
                        
                    modified_adjacency[district].append(best_neighbor)
                    modified_adjacency[best_neighbor].append(district)
        
        # Check again after reconnection
        still_isolated = [d for d, adj in modified_adjacency.items() if len(adj) == 0]
        if still_isolated:
            print(f"Still have {len(still_isolated)} isolated districts after reconnection attempt")
        else:
            print("Successfully reconnected all isolated districts")
    
    # Final check for connectivity
    G = nx.Graph()
    for district, neighbors in modified_adjacency.items():
        for neighbor in neighbors:
            G.add_edge(district, neighbor)
    
    # Check for connected components
    components = list(nx.connected_components(G))
    print(f"Final graph has {len(components)} connected components")
    if len(components) > 1:
        print(f"Largest component has {len(max(components, key=len))} nodes")
        print(f"Smallest component has {len(min(components, key=len))} nodes")
    
    return modified_adjacency, all_removed_edges

def verify_planarity(adjacency, verbose=False):
    """Verify if the graph is planar using NetworkX and optionally print details about non-planar subgraphs"""
    G = nx.Graph()
    for district, neighbors in adjacency.items():
        for neighbor in neighbors:
            G.add_edge(district, neighbor)
    
    is_planar, kuratowski_subgraphs = nx.check_planarity(G)
    
    if not is_planar and verbose:
        print("\nPlanarity check failed. Found the following non-planar Kuratowski subgraphs:")
        try:
            # Ensure kuratowski_subgraphs is iterable before proceeding
            if hasattr(kuratowski_subgraphs, '__iter__'):
                # Save a copy of the generator for later return
                k_subgraphs_list = []
                
                # Get the first few Kuratowski subgraphs
                for i, subgraph in enumerate(kuratowski_subgraphs):
                    k_subgraphs_list.append(subgraph)
                    if i >= 3:  # Limit to first 3 subgraphs
                        break
                        
                    nodes = list(subgraph.nodes())
                    edges = list(subgraph.edges())
                    
                    print(f"  Non-planar subgraph #{i+1}:")
                    print(f"    Nodes ({len(nodes)}): {', '.join(sorted(nodes))}")
                    print(f"    Edges ({len(edges)}):")
                    for u, v in sorted(edges):
                        print(f"      {u} -- {v}")
                
                # Return the copied list to preserve iterability
                return is_planar, G, k_subgraphs_list
            else:
                print(f"  No iterable Kuratowski subgraphs available")
        except Exception as e:
            print(f"  Error printing Kuratowski subgraphs: {e}")
    
    return is_planar, G, [] if not is_planar else None

def main():
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define input and output paths
    kml_path = os.path.join(script_dir, "../processed_data/ge2025_polling_districts_fixed.kml")
    planar_output_path = os.path.join(script_dir, "../processed_data/ge2025_polling_districts_to_adjacent_districts.json")
    
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
    
    # Skip writing non-planar adjacencies
    print("Skipping creation of non-planar adjacencies file...")
    
    # Planarize the graph
    print("Checking initial graph planarity...")
    is_planar, _, _ = verify_planarity(adjacency, verbose=True)
    print(f"Initial graph is {'planar' if is_planar else 'not planar'}")
    
    if is_planar:
        print("Graph is already planar, no changes needed.")
        planar_adjacency = adjacency
    else:
        # Step 1: Detect and remove non-planar edges at quadpoints
        print("Detecting non-planar edges at quadpoints...")
        edges_to_remove = detect_quadpoints(districts, adjacency)
        
        print(f"Found {len(edges_to_remove)} non-planar edges to remove from quadpoints")
        
        # Remove non-planar edges from quadpoints
        intermediate_adjacency = remove_non_planar_edges(adjacency, edges_to_remove)
        
        # Check if the modified graph is planar
        print("Checking planarity after removing quadpoint edges...")
        is_planar, _, _ = verify_planarity(intermediate_adjacency, verbose=True)
        print(f"Graph after quadpoint processing is {'planar' if is_planar else 'still not planar'}")
        
        # Count adjacencies
        total_intermediate = sum(len(adj) for adj in intermediate_adjacency.values())
        print(f"Removed {total_adjacencies - total_intermediate} adjacency relationships in quadpoint step")
        
        # Step 2: If still not planar, use iterative planarization
        if not is_planar:
            print("Applying iterative planarization...")
            
            # Use shared boundary length to determine important adjacencies to preserve
            print("Analyzing all district borders to find significant adjacent pairs...")
            critical_adjacencies = []
            
            # Collect shared boundary lengths for all adjacencies
            boundary_lengths = {}
            count = 0
            total = sum(len(neighbors) for neighbors in adjacency.values()) // 2
            print(f"Analyzing {total} district borders...")
            
            for district_a, neighbors in adjacency.items():
                for district_b in neighbors:
                    if district_a < district_b:  # Process each pair only once
                        count += 1
                        if count % 500 == 0:
                            print(f"Processed {count}/{total} borders ({count/total*100:.1f}%)")
                            
                        pair = (district_a, district_b)
                        
                        # Calculate boundary length if both districts exist
                        if district_a in districts and district_b in districts:
                            try:
                                # Buffer slightly to handle numerical precision
                                buffered_a = districts[district_a].buffer(0.00001)
                                buffered_b = districts[district_b].buffer(0.00001)
                                
                                # Get the intersection
                                if buffered_a.intersects(buffered_b):
                                    intersection = buffered_a.intersection(buffered_b)
                                    
                                    # If they share a boundary (not just a point)
                                    if (intersection.geom_type in ['LineString', 'MultiLineString'] or
                                        (hasattr(intersection, 'length') and intersection.length > 0)):
                                        # Store the length as a measure of adjacency importance
                                        boundary_lengths[pair] = intersection.length
                            except Exception as e:
                                # Silently continue to avoid cluttering output
                                pass
            
            # Once we have all boundary lengths, decide which to preserve
            if boundary_lengths:
                # Find the distribution of boundary lengths
                lengths = list(boundary_lengths.values())
                lengths.sort()
                
                # Use a percentile-based approach - identify boundaries with significant shared borders
                # These are likely more important to preserve for visualization and analysis
                
                # Get basic statistics
                if len(lengths) > 1:
                    min_length = lengths[0]
                    max_length = lengths[-1]
                    median_length = lengths[len(lengths) // 2]
                    
                    # We'll preserve boundaries that are at least 50% of the median length
                    # This will keep important boundaries while removing trivial ones
                    threshold = median_length * 0.5  
                    significant_pairs = [(pair, length) for pair, length in boundary_lengths.items() 
                                        if length >= threshold]
                    
                    # Sort by boundary length (descending)
                    significant_pairs.sort(key=lambda x: x[1], reverse=True)
                    
                    # Take the top pairs, but cap at a very small number to keep planarization possible
                    # Being extremely selective to avoid getting stuck in the algorithm
                    max_preserved = min(50, len(significant_pairs))
                    critical_adjacencies = [pair for pair, _ in significant_pairs[:max_preserved]]
                    
                    print(f"Preserving {len(critical_adjacencies)} adjacencies with significant shared borders")
                    print(f"Border length threshold: {threshold:.6f}")
                    if len(critical_adjacencies) > 0:
                        print(f"Sample preserved adjacencies: {critical_adjacencies[:5]}")
                        print(f"with border lengths: {[boundary_lengths[p] for p in critical_adjacencies[:5]]}")
                else:
                    print("Only one boundary length found, not enough for percentile calculation")
            else:
                print("Warning: No boundary lengths could be calculated")
            
            # Ensure critical adjacencies are present in intermediate_adjacency
            for district_a, district_b in critical_adjacencies:
                # Both districts must exist in the adjacency list
                if district_a in intermediate_adjacency and district_b in intermediate_adjacency:
                    if district_b not in intermediate_adjacency[district_a]:
                        intermediate_adjacency[district_a].append(district_b)
                    if district_a not in intermediate_adjacency[district_b]:
                        intermediate_adjacency[district_b].append(district_a)
            
            planar_adjacency, additional_edges_removed = planarize_graph_iteratively(
                intermediate_adjacency, 
                protected_pairs=critical_adjacencies
            )
            
            print(f"Removed {len(additional_edges_removed)} additional edges using iterative planarization")
            
            # Check if the graph is now planar after iterative planarization
            is_planar, _, _ = verify_planarity(planar_adjacency, verbose=True)
            print(f"After iterative planarization, graph is {'planar' if is_planar else 'still not planar'}")
            
            # Count final adjacencies
            total_modified = sum(len(adj) for adj in planar_adjacency.values())
            print(f"Total edges removed: {total_adjacencies - total_modified}")
        else:
            planar_adjacency = intermediate_adjacency
    
    # Write adjacency to JSON
    print(f"Writing adjacencies to {planar_output_path}...")
    with open(planar_output_path, 'w') as f:
        json.dump(planar_adjacency, f, indent=2)
    
    print("Done!")

if __name__ == "__main__":
    main()