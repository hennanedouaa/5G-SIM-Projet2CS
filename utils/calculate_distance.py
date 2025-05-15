import subprocess
import time
import docker
import heapq
import json

def calculate_distance(coord1, coord2):
    """Calculate Euclidean distance between two coordinates"""
    return math.sqrt((coord1["x"] - coord2["x"])**2 + (coord1["y"] - coord2["y"])**2)

def find_shortest_path(upf_coords, start_upf, end_upf, required_hops=None):
    """
    Find shortest path from start_upf to end_upf
    If required_hops is specified, ensure the path includes exactly that many UPFs in between
    """
    # Create a graph with distances as weights
    graph = {}
    for upf1 in upf_coords:
        graph[upf1] = {}
        for upf2 in upf_coords:
            if upf1 != upf2:
                graph[upf1][upf2] = calculate_distance(upf_coords[upf1], upf_coords[upf2])
    
    # If no required_hops, use standard Dijkstra's algorithm
    if required_hops is None:
        return dijkstra_shortest_path(graph, start_upf, end_upf)
    
    # If required_hops is specified, find all paths with exactly that many hops
    paths = find_paths_with_exact_hops(graph, start_upf, end_upf, required_hops)
    
    # Return the shortest path among those with the required number of hops
    if not paths:
        return None
    
    shortest_path = min(paths, key=lambda p: calculate_path_distance(graph, p))
    return shortest_path

def dijkstra_shortest_path(graph, start, end):
    """Standard Dijkstra's algorithm for shortest path"""
    distances = {node: float('infinity') for node in graph}
    distances[start] = 0
    previous = {node: None for node in graph}
    pq = [(0, start)]
    visited = set()
    
    while pq:
        current_distance, current_node = heapq.heappop(pq)
        
        if current_node == end:
            # Reconstruct path
            path = []
            while current_node is not None:
                path.append(current_node)
                current_node = previous[current_node]
            return list(reversed(path))
            
        if current_node in visited:
            continue
            
        visited.add(current_node)
        
        for neighbor, weight in graph[current_node].items():
            distance = current_distance + weight
            
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous[neighbor] = current_node
                heapq.heappush(pq, (distance, neighbor))
    
    return None  # No path found

def find_paths_with_exact_hops(graph, start, end, hops):
    """Find all paths from start to end with exactly 'hops' intermediate nodes"""
    all_paths = []
    
    def dfs(current, path, visited):
        if current == end:
            # Check if we have exactly 'hops' intermediate nodes (excluding start and end)
            if len(path) - 2 == hops:
                all_paths.append(path.copy())
            return
        
        # If path length would exceed hops+2 (start and end), stop this branch
        if len(path) > hops + 2:
            return
        
        for neighbor in graph[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                path.append(neighbor)
                dfs(neighbor, path, visited)
                path.pop()
                visited.remove(neighbor)
    
    dfs(start, [start], {start})
    return all_paths

def calculate_path_distance(graph, path):
    """Calculate total distance of a path"""
    total = 0
    for i in range(len(path) - 1):
        total += graph[path[i]][path[i+1]]
    return total

def update_ue_routing_with_paths(paths, num_upfs, edge_upfs):
    """Update UE routing configuration with calculated paths"""
    # First read existing config
    custom_config_dir = "./config/custom"
    routing_file = os.path.join(custom_config_dir, "uerouting.yaml")
    
    try:
        with open(routing_file, "r") as f:
            ue_routing = yaml.safe_load(f)
    except FileNotFoundError:
        ue_routing = generate_uerouting_config(num_upfs, edge_upfs)
    
    # Update routing with calculated paths
    for edge_idx, path in paths.items():
        upf_name = f"i-upf{edge_idx}" if edge_idx > 1 else "i-upf"
        
        # Get the routing info (should be the first entry for each UPF in the edge)
        if "userPlaneRouting" in ue_routing and "routing" in ue_routing["userPlaneRouting"]:
            routing_entries = ue_routing["userPlaneRouting"]["routing"]
            
            # Find and update the entry for this edge UPF
            for entry in routing_entries:
                if "sourceUPF" in entry and entry["sourceUPF"] == upf_name:
                    # Update the path with the calculated sequence
                    path_seq = [node for node in path if node != upf_name]  # Remove start node to avoid duplication
                    entry["path"] = path_seq
                    break
    
    # Write updated config back
    with open(routing_file, "w") as f:
        yaml.dump(ue_routing, f, default_flow_style=False)
    
    return ue_routing
