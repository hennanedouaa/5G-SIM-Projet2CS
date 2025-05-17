import math
import heapq
import random
import argparse
from collections import defaultdict

class UPFNetwork:
    def __init__(self):
        self.graph = defaultdict(dict)
        self.upf_loads = defaultdict(int)
        self.upf_positions = {}
        self.psa_position = None
        self.psa_upf = "psa"
        self.edge_upfs = set()

    def add_upf(self, upf_id, position):
        self.upf_positions[upf_id] = position

    def set_psa(self, position):
        self.psa_position = position
        self.upf_positions[self.psa_upf] = position

    def connect_upfs(self, upf1, upf2):
        distance = math.dist(self.upf_positions[upf1], self.upf_positions[upf2])
        self.graph[upf1][upf2] = distance
        self.graph[upf2][upf1] = distance

    def get_path_cost(self, path, alpha=1.0, beta=0.5):
        total_cost = 0
        for i in range(len(path)-1):
            current = path[i]
            next_node = path[i+1]
            distance = self.graph[current][next_node]
            load_cost = self.upf_loads[next_node]
            total_cost += alpha * distance + beta * load_cost
        return total_cost

    def constrained_dijkstra(self, start, end, exact_hops, alpha=1.0, beta=0.5):
        heap = []
        heapq.heappush(heap, (0, 1, start, [start]))

        while heap:
            current_cost, current_len, current_node, path = heapq.heappop(heap)

            if current_len == exact_hops:
                if current_node == end:
                    return path, current_cost
                continue

            for neighbor, distance in self.graph[current_node].items():
                if neighbor in path:
                    continue
                if neighbor in self.edge_upfs and neighbor != end:
                    continue
                new_path = path + [neighbor]
                step_cost = alpha * distance + beta * self.upf_loads[neighbor]
                new_cost = current_cost + step_cost
                heapq.heappush(heap, (new_cost, current_len + 1, neighbor, new_path))

        raise ValueError(f"No valid path of exactly {exact_hops} nodes from {start} to {end}")


def rename_upfs(network, edge_upfs):
    renamed_positions = {}
    renamed_loads = {}
    renamed_graph = defaultdict(dict)
    old_to_new = {}
    i = 1
    j = 1

    for upf in network.upf_positions:
        if upf == network.psa_upf:
            new_name = network.psa_upf
        elif upf in edge_upfs:
            new_name = f"edge-upf{i}"
            i += 1
        else:
            new_name = f"i-up{j}"
            j += 1
        old_to_new[upf] = new_name

    # Update positions and loads
    for old, new in old_to_new.items():
        renamed_positions[new] = network.upf_positions[old]
        renamed_loads[new] = network.upf_loads[old]

    # Update graph
    for old_src, neighbors in network.graph.items():
        new_src = old_to_new[old_src]
        for old_dst, dist in neighbors.items():
            new_dst = old_to_new[old_dst]
            renamed_graph[new_src][new_dst] = dist

    # Apply changes to network
    network.upf_positions = renamed_positions
    network.upf_loads = renamed_loads
    network.graph = renamed_graph
    network.edge_upfs = {old_to_new[u] for u in edge_upfs}
    return old_to_new


def get_coordinates(prompt, default=None, random_range=10):
    if default == "random":
        return (random.uniform(0, random_range), random.uniform(0, random_range))
    while True:
        coords = input(prompt).strip()
        if not coords and default is not None:
            return default
        try:
            x, y = map(float, coords.split())
            return (x, y)
        except ValueError:
            print("Invalid input. Enter two numbers separated by space.")


def generate_network(num_ue, num_upfs, m, skip=False):
    print("\n🔧 Configuring network...")
    max_e = num_upfs - m + 1
    print(f"📈 Maximum edge UPFs allowed: {max_e}")

    network = UPFNetwork()
    num_gnb = num_ue // 2
    gnbs = {}

    print(f"\n📡 {'Generating' if skip else 'Enter'} coordinates for {num_gnb} gNBs:")
    for i in range(1, num_gnb + 1):
        pos = (0.0, float(i)) if skip else get_coordinates(f"gNB{i} (x y): ", (0.0, float(i)))
        gnbs[f"gnb{i}"] = pos
        print(f"  ➤ gNB{i}: {pos}")

    print(f"\n🖧 {'Generating' if skip else 'Enter'} coordinates for {num_upfs} UPFs:")
    for i in range(1, num_upfs + 1):
        pos = (random.uniform(0, 10), random.uniform(0, 10)) if skip else get_coordinates(f"UPF{i} (x y): ")
        network.add_upf(f"upf{i}", pos)
        print(f"  ➤ UPF{i}: {pos}")

    print("\n🛡 PSA configuration:")
    psa_pos = (random.uniform(0, 10), random.uniform(0, 10)) if skip else get_coordinates("Enter PSA coordinates (x y): ")
    network.set_psa(psa_pos)
    print(f"  ➤ PSA: {psa_pos}")

    all_upfs = list(network.upf_positions.keys())
    for i in range(len(all_upfs)):
        for j in range(i+1, len(all_upfs)):
            network.connect_upfs(all_upfs[i], all_upfs[j])

    return network, gnbs, max_e


def assign_and_calculate(network, gnbs, num_ue, num_upfs, m, alpha=1.0, beta=0.5):
    edge_upfs = set()
    gnb_assignments = {}

    for gnb_id, gnb_pos in gnbs.items():
        min_cost = float('inf')
        best_upf = None

        for upf_id in network.upf_positions:
            if upf_id == network.psa_upf:
                continue
            distance = math.dist(gnb_pos, network.upf_positions[upf_id])
            load = network.upf_loads[upf_id]
            cost = alpha * distance + beta * load
            if cost < min_cost:
                min_cost = cost
                best_upf = upf_id

        best_upf = best_upf or network.psa_upf
        gnb_assignments[gnb_id] = best_upf
        edge_upfs.add(best_upf)
        network.upf_loads[best_upf] += 1

    network.edge_upfs = edge_upfs
    rename_map = rename_upfs(network, edge_upfs)

    # Reverse rename map for printing original names
    reverse_map = {v: k for k, v in rename_map.items()}
    gnb_assignments = {g: rename_map[u] for g, u in gnb_assignments.items()}

    edge_to_gnbs = defaultdict(list)
    for gnb, upf in gnb_assignments.items():
        edge_to_gnbs[upf].append(gnb)

    print(f"\n📊 Number of edge UPFs: {len(network.edge_upfs)}")
    print("📍 Edge UPF Assignments:")
    for i, (upf, gnb_list) in enumerate(edge_to_gnbs.items(), 1):
        if upf == network.psa_upf:
            continue
        original_name = reverse_map[upf]
        gnb_list_str = ", ".join(gnb_list)
        print(f"  ➤ {original_name} was chosen to be {upf} for gNBs: {gnb_list_str}")

    i_upfs = sorted(set(network.upf_positions.keys()) - network.edge_upfs - {network.psa_upf},
                    key=lambda x: network.upf_loads[x])
    print(f"\n🛤 Number of intermediate UPFs: {len(i_upfs)}")
    print(f"🛡 PSA UPF: {network.psa_upf} at {network.psa_position}")

    print(f"\n🚚 Paths from edge UPFs to PSA (max {m-1} intermediate UPFs):")
    for edge in network.edge_upfs:
        if edge == network.psa_upf:
            continue
        try:
            path, cost = network.constrained_dijkstra(edge, network.psa_upf, m, alpha, beta)
            print(f"  ➤ {edge}: {' -> '.join(path)} (cost: {cost:.2f}, hops: {len(path)-1})")
            for upf in path[1:-1]:
                network.upf_loads[upf] += 1
        except ValueError as e:
            print(f"  ✖ {edge}: {e}")

    print("\n📶 gNB to UE Assignments:")
    gnb_to_ues = defaultdict(list)
    for i, gnb in enumerate(gnbs.keys(), 1):
        gnb_to_ues[gnb].extend([f"ue{i*2-1}", f"ue{i*2}"])

    for gnb, ue_list in gnb_to_ues.items():
        print(f"  ➤ {gnb}: {ue_list}")


def main():
    parser = argparse.ArgumentParser(description="5G Network Path Calculator")
    parser.add_argument("--skip", action="store_true", help="Skip coordinate input and generate random network")
    args = parser.parse_args()

    print("📡 5G Network Path Calculation with PSA")
    print("======================================\n")

    num_ue = int(input("👥 Enter number of UEs: "))
    num_upfs = int(input("🔢 Enter number of UPFs (n): "))
    m = int(input("🔗 Enter number of UPFs each UE passes by (m): "))

    network, gnbs, max_e = generate_network(num_ue, num_upfs, m, args.skip)

    alpha = 1.0
    beta = 0.5

    assign_and_calculate(network, gnbs, num_ue, num_upfs, m, alpha, beta)


if __name__ == "__main__":
    main()

