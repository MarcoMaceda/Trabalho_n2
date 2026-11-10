"""
Build data/edges.csv (from, to, distance, danger_level) from data/shrines.csv.

The graph is a DIRECTED graph (digraph), so an edge A -> B does not imply
that B -> A exists.

Rules:
  1. Every shrine gets one outgoing edge to each of its K nearest neighbours,
     as long as that neighbour is closer than MAX_DIST pixels.
  1b. If NO_REVERSE_DUPLICATES is True, whenever both A -> B and B -> A exist
     only ONE of them is kept (chosen at random, reproducible via SEED).
  2. directed_dfs needs a path from any shrine to any other one, so the graph
     must be STRONGLY connected. If it is not, "bridge" edges are added.
     With NO_REVERSE_DUPLICATES the bridges are added ONE direction at a time,
     choosing edges that close a cycle without being the direct reverse of an
     existing edge. Only if that is impossible does it fall back to adding
     both directions.
  3. Every edge gets two weights:
       distance     = straight-line distance in map pixels
       danger_level = number of its two endpoints located in a dangerous
                      region (0, 1 or 2)

Usage:
    python edges_creator.py
"""
import csv
import math
import random
import statistics
from collections import Counter, namedtuple

NODES_FILE = "data/shrines.csv"
EDGES_FILE = "data/edges.csv"

K = 2                 # number of nearest neighbours each shrine connects to
MAX_DIST = 200.0      # maximum edge length in pixels (None = no limit)

# True  -> never keep both A -> B and B -> A (fewer edges)
# False -> original behaviour (reverse duplicates allowed)
NO_REVERSE_DUPLICATES = True
SEED = 0              # which direction survives in a mutual pair

# Regions considered dangerous. These names must match the "region" column
# of shrines.csv exactly (the script warns you if one of them is not found).
DANGEROUS_REGIONS = {
    "Ridgeland", "Tabantha", "Hebra", "Wasteland", "Eldin", "Central", "Faron",
}

# One shrine = name, region and its position on the map image
Shrine = namedtuple("Shrine", ["name", "region", "x", "y"])


def load_nodes(path):
    """Read the shrines CSV and return a dict {id: Shrine}.
    Shrines that have no coordinates yet are skipped."""
    nodes = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["x"] and row["y"]:
                nodes[int(row["id"])] = Shrine(
                    row["name"], row["region"], float(row["x"]), float(row["y"])
                )
    return nodes


def build_adjacency(node_ids, edges):
    """Turn a set of directed edges (source, target) into an adjacency
    dict {node: set of nodes reachable with ONE edge}."""
    adjacency = {n: set() for n in node_ids}
    for source, target in edges:
        adjacency[source].add(target)
    return adjacency


def reachable_from(start, adjacency):
    """Iterative depth-first search: return every node that can be reached
    from `start` by following edge directions (including `start` itself)."""
    visited = {start}
    stack = [start]
    while stack:
        current = stack.pop()              # LIFO -> goes deep before wide
        for neighbour in adjacency[current]:
            if neighbour not in visited:
                visited.add(neighbour)
                stack.append(neighbour)
    return visited


def strongly_connected_components(node_ids, adjacency):
    """Group the nodes into strongly connected components (SCCs).
    Two nodes are in the same SCC if each one can reach the other.
    The graph is strongly connected when there is exactly one SCC."""
    reach = {n: reachable_from(n, adjacency) for n in node_ids}
    assigned = set()
    components = []
    for n in node_ids:
        if n in assigned:
            continue
        # n and m are in the same SCC if n reaches m AND m reaches n
        component = [m for m in reach[n] if n in reach[m]]
        assigned.update(component)
        components.append(component)
    return components


def danger_level(a, b, nodes):
    """0 = no endpoint in a dangerous region, 1 = one endpoint, 2 = both."""
    return (int(nodes[a].region in DANGEROUS_REGIONS)
            + int(nodes[b].region in DANGEROUS_REGIONS))


def main():
    nodes = load_nodes(NODES_FILE)
    node_ids = sorted(nodes)

    def distance(a, b):
        """Euclidean distance (in pixels) between two shrines."""
        return math.hypot(nodes[a].x - nodes[b].x, nodes[a].y - nodes[b].y)

    # Sanity check: a typo in DANGEROUS_REGIONS would silently make some
    # regions "safe", so warn about names that match no shrine.
    known_regions = {s.region for s in nodes.values()}
    unknown = DANGEROUS_REGIONS - known_regions
    if unknown:
        print(f"WARNING: regions not found in {NODES_FILE}: {sorted(unknown)}")
        print(f"         regions available: {sorted(known_regions)}")

    # ---- Step 1: directed K-nearest-neighbour edges -----------------------
    edges = set()              # set of (source, target) pairs
    kth_distances = []         # distance to the K-th neighbour of each node
    for source in node_ids:
        # all other shrines sorted from the closest to the farthest
        neighbours = sorted((distance(source, other), other)
                            for other in node_ids if other != source)
        kth_distances.append(neighbours[K - 1][0])
        for dist, target in neighbours[:K]:
            if MAX_DIST is None or dist <= MAX_DIST:
                edges.add((source, target))     # only source -> target

    # ---- Step 1b: drop one direction of every mutual pair ------------------
    if NO_REVERSE_DUPLICATES:
        rng = random.Random(SEED)
        removed = 0
        for a, b in sorted(edges):              # sorted() = a copy, safe to edit
            if a < b and (b, a) in edges:
                edges.discard(rng.choice([(a, b), (b, a)]))
                removed += 1
        print(f"Reverse duplicates removed: {removed}")

    adjacency = build_adjacency(node_ids, edges)
    components = strongly_connected_components(node_ids, adjacency)
    print(f"{len(node_ids)} nodes | distance to the K={K} neighbour: "
          f"median {statistics.median(kth_distances):.0f}, "
          f"max {max(kth_distances):.0f}")
    print(f"Strongly connected components before bridges: {len(components)}")

    # ---- Step 2: bridges until the graph is strongly connected ------------
    bridges = []               # (distance, source, target)
    while len(components) > 1:
        # which component does each node belong to?
        component_of = {n: i for i, comp in enumerate(components) for n in comp}
        # pairs of nodes in different components
        cross = [(u, v) for u in node_ids for v in node_ids
                 if u != v and component_of[u] != component_of[v]]

        added = []
        if NO_REVERSE_DUPLICATES:
            reach = {n: reachable_from(n, adjacency) for n in node_ids}
            # Tier 1: edge u -> v that closes a cycle (v already reaches u)
            # and is not the direct reverse of an existing edge.
            tier1 = [(distance(u, v), u, v) for u, v in cross
                     if u in reach[v] and (v, u) not in edges]
            # Tier 2: no cycle can be closed yet, so just add a new one-way
            # link (reachability grows, tier 1 will find candidates later).
            tier2 = [(distance(u, v), u, v) for u, v in cross
                     if (u, v) not in edges and (v, u) not in edges]
            for tier in (tier1, tier2):
                if tier:
                    dist, u, v = min(tier)
                    added = [(dist, u, v)]
                    break

        if not added:
            # Original behaviour / last resort: both directions between the
            # closest pair, which always merges the two components.
            dist, u, v = min((distance(u, v), u, v) for u, v in cross if u < v)
            added = [(dist, u, v), (dist, v, u)]

        for dist, u, v in added:
            edges.add((u, v))
            bridges.append((dist, u, v))
        adjacency = build_adjacency(node_ids, edges)
        components = strongly_connected_components(node_ids, adjacency)

    for dist, a, b in bridges:
        print(f"  bridge: {nodes[a].name} -> {nodes[b].name} ({dist:.0f} px)")

    # ---- Step 3: write the CSV with both weights ---------------------------
    with open(EDGES_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["from", "to", "distance", "danger_level"])
        for source, target in sorted(edges):
            writer.writerow([source, target,
                             f"{distance(source, target):.1f}",
                             danger_level(source, target, nodes)])

    # ---- Summary to help you tune K and MAX_DIST ---------------------------
    out_degree = [len(adjacency[n]) for n in node_ids]
    in_degree = Counter(target for _, target in edges)
    mutual_pairs = sum(1 for a, b in edges if a < b and (b, a) in edges)
    danger_counts = Counter(danger_level(a, b, nodes) for a, b in edges)

    print(f"{len(edges)} directed edges -> {EDGES_FILE} "
          f"({mutual_pairs} pairs exist in both directions)")
    print(f"Out-degree: min {min(out_degree)}, "
          f"median {statistics.median(out_degree)}, max {max(out_degree)}")
    print(f"In-degree:  min {min(in_degree[n] for n in node_ids)}, "
          f"median {statistics.median(in_degree[n] for n in node_ids)}, "
          f"max {max(in_degree[n] for n in node_ids)}")
    print("Edges per danger level: "
          + ", ".join(f"{lvl}: {danger_counts[lvl]}" for lvl in (0, 1, 2)))


if __name__ == "__main__":
    main()