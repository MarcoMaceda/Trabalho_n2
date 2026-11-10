"""
Draws the map with the shrines (nodes) and the connections (edges) of the graph.

Reads:
    data/botw_map.jpg   map image
    data/shrines.csv    nodes (id, name, region, x, y)
    data/edges.csv      edges (from, to, distance, danger_level)

Visualization:
    - Each edge is an arrow (the graph is DIRECTED). If both A -> B and
      B -> A exist, the two arrows curve to opposite sides and do not overlap.
    - Edge color = danger_level:  0 green | 1 orange | 2 red
    - Node color = dangerous region (red) or safe region (blue)

Usage:
    pip install matplotlib pillow
    python plot_graph.py                 # opens the window
    python plot_graph.py --labels        # writes the id next to each node
    python plot_graph.py --save graph.png
    python plot_graph.py --path 5 87     # (optional) highlights nodes 5 and 87
"""
import argparse
import csv

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

from edges_creator import DANGEROUS_REGIONS

# ---- Settings -------------------------------------------------------------
MAP_IMAGE = "data/botw_map.jpg"
NODES_FILE = "data/shrines.csv"
EDGES_FILE = "data/edges.csv"

EDGE_COLORS = {0: "#2ecc71", 1: "#f39c12", 2: "#e74c3c"}
NODE_SAFE = "#3498db"
NODE_DANGER = "#c0392b"
# ---------------------------------------------------------------------------


def load_nodes(path):
    """Returns {id: dict(name, region, x, y)} (skips shrines without coordinates)."""
    nodes = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["x"] and row["y"]:
                nodes[int(row["id"])] = {
                    "name": row["name"],
                    "region": row["region"],
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                }
    return nodes


def load_edges(path):
    """Returns a list of (from, to, distance, danger_level)."""
    with open(path, newline="", encoding="utf-8") as f:
        return [(int(r["from"]), int(r["to"]),
                 float(r["distance"]), int(r["danger_level"]))
                for r in csv.DictReader(f)]


def main():
    parser = argparse.ArgumentParser(description="Shrine graph plot")
    parser.add_argument("--labels", action="store_true",
                        help="shows the id of each node")
    parser.add_argument("--save", metavar="FILE",
                        help="saves the image instead of opening the window")
    parser.add_argument("--hide-edges", action="store_true",
                        help="shows only the nodes")
    args = parser.parse_args()

    nodes = load_nodes(NODES_FILE)
    edges = load_edges(EDGES_FILE)
    img = mpimg.imread(MAP_IMAGE)

    fig, ax = plt.subplots(figsize=(14, 12))
    ax.imshow(img)

    # ---- Edges -----------------------------------------------------------
    if not args.hide_edges:
        for a, b, dist, danger in edges:
            if a not in nodes or b not in nodes:
                continue
            arrow = FancyArrowPatch(
                (nodes[a]["x"], nodes[a]["y"]),
                (nodes[b]["x"], nodes[b]["y"]),
                arrowstyle="-|>", mutation_scale=8,
                connectionstyle="arc3,rad=0.12",   # curve -> A->B and B->A are separated
                color=EDGE_COLORS[danger], linewidth=1.1, alpha=0.8,
                shrinkA=4, shrinkB=4,              # does not cover the node circles
                zorder=2,
            )
            ax.add_patch(arrow)

    # ---- Nodes -----------------------------------------------------------
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    colors = [NODE_DANGER if n["region"] in DANGEROUS_REGIONS else NODE_SAFE
              for n in nodes.values()]
    ax.scatter(xs, ys, c=colors, s=45, edgecolors="white", linewidths=0.8,
               zorder=3)

    if args.labels:
        for i, n in nodes.items():
            ax.annotate(str(i), (n["x"], n["y"]), xytext=(4, 4),
                        textcoords="offset points", fontsize=7,
                        color="white", zorder=4,
                        bbox=dict(boxstyle="round,pad=0.1", fc="black",
                                  alpha=0.5, lw=0))

    # ---- Legend ----------------------------------------------------------
    legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=NODE_SAFE,
               markeredgecolor="white", markersize=8, label="Shrine (safe region)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=NODE_DANGER,
               markeredgecolor="white", markersize=8, label="Shrine (dangerous region)"),
        Line2D([0], [0], color=EDGE_COLORS[0], lw=2, label="Danger 0 edge"),
        Line2D([0], [0], color=EDGE_COLORS[1], lw=2, label="Danger 1 edge"),
        Line2D([0], [0], color=EDGE_COLORS[2], lw=2, label="Danger 2 edge"),
    ]
    ax.legend(handles=legend, loc="lower left", framealpha=0.9)

    ax.set_title(f"Shrine graph: {len(nodes)} nodes, {len(edges)} directed edges")
    ax.axis("off")
    fig.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=200, bbox_inches="tight")
        print(f"Image saved to {args.save}")
    else:
        plt.show()


if __name__ == "__main__":
    main()