import csv
from graph import Digraph, Node, WeightedEdge


def load_map(nodes_file="data/shrines.csv", edges_file="data/edges.csv"):
    g = Digraph()
    with open(nodes_file, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g.add_node(Node(row["id"]))
    with open(edges_file, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g.add_edge(WeightedEdge(Node(row["from"]), Node(row["to"]),
                                    float(row["distance"]),
                                    int(row["danger_level"])))
    return g


def get_best_path(digraph, start, end, path, max_danger, best_dist, best_path):
    if not digraph.has_node(Node(start)) or not digraph.has_node(Node(end)):
        raise ValueError('Invalid start or end node')
    if start == end:
        return (path[0][:], path[1])
    for edge in sorted(digraph.get_edges_for_node(Node(start)),
                       key=lambda e: e.get_total_distance()):
        nxt = edge.get_destination().get_name()
        if nxt in path[0]:                       # evita ciclos
            continue
        new_dist = path[1] + edge.get_total_distance()
        new_danger = path[2] + edge.get_danger_level()
        if new_danger > max_danger:              # restrição de perigo
            continue
        if best_path is not None and new_dist >= best_dist:   # poda
            continue
        if best_path is None and new_dist > best_dist:        # limite inicial
            continue
        result = get_best_path(digraph, nxt, end,
                               [path[0] + [nxt], new_dist, new_danger],
                               max_danger, best_dist, best_path)
        if result is not None:
            best_path, best_dist = result
    return (best_path, best_dist) if best_path is not None else None


def directed_dfs(digraph, start, end, max_total_dist, max_dist_outdoors):
    result = get_best_path(digraph, start, end, [[start], 0, 0],
                           max_dist_outdoors, max_total_dist, None)
    if result is None:
        raise ValueError('No path satisfies the constraints')
    return result[0]