"""
Rota mais rápida vs. rota mais rápida e segura entre dois santuários
aleatórios de Hyrule.

Usa as classes do graph.py (Node, WeightedEdge, Digraph) tal como estão:
    WeightedEdge.get_distance()      -> distância em píxeis
    WeightedEdge.get_danger_level()  -> 0, 1 ou 2

Ficheiros necessários (na mesma pasta):
    graph.py
    data/shrines.csv, data/edges.csv, data/botw_map.jpg

Uso:
    python rota_hyrule.py                     # par aleatório
    python rota_hyrule.py --seed 7            # par aleatório reproduzível
    python rota_hyrule.py --different         # só pares com rotas diferentes
    python rota_hyrule.py --start 33 --end 16 # par escolhido
    python rota_hyrule.py --save rota.png     # grava a imagem
"""

import sys; print(sys.executable)
import argparse
import csv
import random
import sys

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from graph import Digraph, Node, WeightedEdge

NODES_FILE = "data/shrines.csv"
EDGES_FILE = "data/edges.csv"
MAP_IMAGE = "data/botw_map.jpg"

NO_LIMIT = 10 ** 9
sys.setrecursionlimit(10000)


# ---------------------------------------------------------------------------
# Problema 2: construir o mapa
# ---------------------------------------------------------------------------
def load_map(nodes_file=NODES_FILE, edges_file=EDGES_FILE):
    """Devolve (digraph, info). info = {id: {name, region, x, y}}."""
    g = Digraph()
    info = {}
    with open(nodes_file, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g.add_node(Node(row["id"]))
            info[row["id"]] = {
                "name": row["name"],
                "region": row["region"],
                "x": float(row["x"]) if row["x"] else None,
                "y": float(row["y"]) if row["y"] else None,
            }
    with open(edges_file, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            g.add_edge(WeightedEdge(Node(row["from"]), Node(row["to"]),
                                    float(row["distance"]),
                                    int(row["danger_level"])))
    return g, info


# ---------------------------------------------------------------------------
# Problema 3: pesquisa em profundidade com poda
# ---------------------------------------------------------------------------
def get_best_path(digraph, start, end, path, max_danger, best_dist, best_path):
    """
    path       = [lista de nomes de nós, distância acumulada, perigo acumulado]
    best_dist  = distância do melhor caminho até agora (ou o limite inicial)
    best_path  = melhor caminho até agora (None se ainda não há nenhum)
    Devolve (caminho, distância) ou None.
    """
    if start == end:
        return (path[0][:], path[1])

    for edge in digraph.get_edges_for_node(Node(start)):
        nxt = edge.get_destination().get_name()
        if nxt in path[0]:                       # evita ciclos
            continue
        new_dist = path[1] + edge.get_distance()
        new_danger = path[2] + edge.get_danger_level()
        if new_danger > max_danger:              # restrição de perigo
            continue
        if best_path is None:                    # ainda sem solução:
            if new_dist > best_dist:             #   só respeita o limite
                continue
        elif new_dist >= best_dist:              # poda: já não melhora
            continue
        result = get_best_path(digraph, nxt, end,
                               [path[0] + [nxt], new_dist, new_danger],
                               max_danger, best_dist, best_path)
        if result is not None:
            best_path, best_dist = result
    return (best_path, best_dist) if best_path is not None else None


def directed_dfs(digraph, start, end, max_total_dist, max_danger):
    """Caminho mais curto de start a end com distância <= max_total_dist e
    perigo <= max_danger. ValueError se não existir."""
    if not digraph.has_node(Node(start)) or not digraph.has_node(Node(end)):
        raise ValueError("Nó inexistente")
    result = get_best_path(digraph, start, end, [[start], 0, 0],
                           max_danger, max_total_dist, None)
    if result is None:
        raise ValueError("Nenhum caminho cumpre as restrições")
    return result[0]


# ---------------------------------------------------------------------------
# As duas rotas
# ---------------------------------------------------------------------------
def path_stats(g, path):
    """(distância total, perigo total) de uma lista de nomes de nós."""
    dist, danger = 0.0, 0
    for a, b in zip(path, path[1:]):
        edge = next(e for e in g.get_edges_for_node(Node(a))
                    if e.get_destination().get_name() == b)
        dist += edge.get_distance()
        danger += edge.get_danger_level()
    return dist, danger


def fastest_path(g, start, end):
    """Rota mais rápida: sem limite de perigo."""
    return directed_dfs(g, start, end, NO_LIMIT, NO_LIMIT)


def fastest_safest_path(g, start, end, danger_of_fastest):
    """Rota com o perigo mínimo possível e, dentro desse perigo, a mais curta.
    O perigo é inteiro, por isso pesquisa binária no limite de perigo."""
    lo, hi = 0, int(danger_of_fastest)           # hi é sempre viável
    while lo < hi:
        mid = (lo + hi) // 2
        try:
            directed_dfs(g, start, end, NO_LIMIT, mid)
            hi = mid
        except ValueError:
            lo = mid + 1
    return directed_dfs(g, start, end, NO_LIMIT, lo)


# ---------------------------------------------------------------------------
# Apresentação
# ---------------------------------------------------------------------------
def describe(title, g, info, path):
    dist, danger = path_stats(g, path)
    print(f"\n{title}")
    print(f"  {len(path) - 1} passos | distância {dist:.1f} px | perigo {danger}")
    print("  " + " -> ".join(f"{n} ({info[n]['name']})" for n in path))
    return dist, danger


def draw(info, path_fast, path_safe, start, end, stats_fast, stats_safe, out):
    fig, ax = plt.subplots(figsize=(14, 12))
    ax.imshow(mpimg.imread(MAP_IMAGE))

    pts = [(v["x"], v["y"]) for v in info.values() if v["x"] is not None]
    ax.scatter(*zip(*pts), s=14, c="white", alpha=0.5, zorder=2)

    same = path_fast == path_safe

    def trace(path, color, width, style):
        xs = [info[n]["x"] for n in path]
        ys = [info[n]["y"] for n in path]
        ax.plot(xs, ys, style, color=color, lw=width, zorder=3,
                solid_capstyle="round")
        ax.scatter(xs, ys, s=30, c=color, edgecolors="white", zorder=4)

    trace(path_fast, "#e74c3c", 5, "-")
    trace(path_safe, "#2ecc71", 2.5, "--" if same else "-")

    for n, marker, lbl in ((start, "*", "Partida"), (end, "X", "Destino")):
        ax.scatter(info[n]["x"], info[n]["y"], s=380, marker=marker, c="gold",
                   edgecolors="black", linewidths=1.5, zorder=6)
        ax.annotate(f"{lbl}: {info[n]['name']}", (info[n]["x"], info[n]["y"]),
                    xytext=(10, 10), textcoords="offset points", fontsize=10,
                    color="white", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.25", fc="black", alpha=0.75))

    ax.legend(handles=[
        Line2D([0], [0], color="#e74c3c", lw=5,
               label=f"Mais rápida: {stats_fast[0]:.0f} px, perigo {stats_fast[1]}"),
        Line2D([0], [0], color="#2ecc71", lw=2.5,
               label=f"Mais rápida e segura: {stats_safe[0]:.0f} px, "
                     f"perigo {stats_safe[1]}"),
    ], loc="lower left", framealpha=0.9)

    ax.set_title(f"{info[start]['name']} ({start})  ->  {info[end]['name']} ({end})"
                 + ("   [as duas rotas coincidem]" if same else ""))
    ax.axis("off")
    fig.tight_layout()
    if out:
        fig.savefig(out, dpi=200, bbox_inches="tight")
        print(f"\nImagem gravada em {out}")
    else:
        plt.show()


def main():
    p = argparse.ArgumentParser(description="Rota mais rápida vs mais rápida e segura")
    p.add_argument("--seed", type=int, help="semente do gerador aleatório")
    p.add_argument("--start", help="id do santuário de partida")
    p.add_argument("--end", help="id do santuário de destino")
    p.add_argument("--save", metavar="FICHEIRO", help="grava a imagem")
    p.add_argument("--different", action="store_true",
                   help="sorteia pares até as duas rotas serem diferentes")
    args = p.parse_args()

    g, info = load_map()
    print(f"Mapa carregado: {len(g.nodes)} nós, "
          f"{sum(len(e) for e in g.edges.values())} arestas")
    ids = [i for i, v in info.items() if v["x"] is not None]

    rng = random.Random(args.seed)
    while True:
        start = args.start or rng.choice(ids)
        end = args.end or rng.choice([i for i in ids if i != start])
        if start == end:
            sys.exit("A partida e o destino têm de ser diferentes.")
        path_fast = fastest_path(g, start, end)
        danger_fast = path_stats(g, path_fast)[1]
        path_safe = fastest_safest_path(g, start, end, danger_fast)
        if not args.different or path_fast != path_safe \
                or (args.start and args.end):
            break

    print(f"\nPartida: {start} ({info[start]['name']}, {info[start]['region']})")
    print(f"Destino: {end} ({info[end]['name']}, {info[end]['region']})")
    stats_fast = describe("Rota MAIS RÁPIDA (sem limite de perigo)",
                          g, info, path_fast)
    stats_safe = describe("Rota MAIS RÁPIDA E SEGURA (perigo mínimo)",
                          g, info, path_safe)

    if path_fast == path_safe:
        print("\nAs duas rotas coincidem: a mais rápida já é a menos perigosa.")
    else:
        print(f"\nCusto de ser mais seguro: +{stats_safe[0] - stats_fast[0]:.1f} px, "
              f"perigo {stats_fast[1]} -> {stats_safe[1]}")

    draw(info, path_fast, path_safe, start, end, stats_fast, stats_safe, args.save)


if __name__ == "__main__":
    main()
