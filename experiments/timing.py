"""
Scaling table of the paper (Table "Time in seconds to hash all nodes of a graph with n nodes").

Times the local hashes, the local Merkle hashes and the quadratic ordered baselines on one family of ordered digraphs
and prints one JSON row per graph size with the median time in seconds of each hash over the repetitions.

  random       two labels and 2n randomly drawn edges, duplicates discarded, ports in order of insertion;
               a new random graph is drawn for every repetition
  cycle        the directed n-cycle in which node 0 has a different label (a single deterministic graph)
  permutation  all labels equal; port 0 follows a random n-cycle and port 1 a random permutation, so every port
               permutes the nodes and all nodes have isomorphic ordered unfoldings (the worst case of the
               strongly connected canonization); a new random graph is drawn for every repetition

Usage: python experiments/timing.py {random,cycle,permutation} [--reps R] [--quadratic-max N] [--merkle-max N] n [n ...]

The paper's table was produced with
  python experiments/timing.py random      --reps 3 1000 4000 16000 64000                (results/timing_random.jsonl)
  python experiments/timing.py cycle       --reps 1 1000 4000 16000 64000                (results/timing_cycle.jsonl)
  python experiments/timing.py permutation --reps 3 --merkle-max 4000 1000 4000 16000 64000
                                                                           (results/timing_permutation.jsonl)

Columns: scc = size of the largest strongly connected component; HL = local hash; HB = bisimulation hash;
ord_local = ordered local hash; HMl_unord / HMl_ord = local Merkle hash of the graph as an unordered / ordered graph;
HO_all = ordered node hash of every node; HMg_ord = global Merkle hash of the ordered graph. HO_all is quadratic and
is only run for n <= --quadratic-max; HMg_ord is only run for n <= --merkle-max (default: all sizes).
"""
import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.setrecursionlimit(100000)

import networkx as nx

from dihash.local_hash import local_hash, LocalHashVariant as V
from dihash.ordered_hash import ordered_node_hash, ordered_local_hash
from dihash.merkle_hash import merkle_hash, OrderedGlobalMH, OrderedLocalMH, LocalMH


def random_ordered(n, seed):
    rng = random.Random(seed)
    g = nx.DiGraph()
    for i in range(n):
        g.add_node(i, label=rng.choice("ab"))
    for _ in range(2 * n):
        u, v = rng.randrange(n), rng.randrange(n)
        if not g.has_edge(u, v):
            g.add_edge(u, v, port=g.out_degree(u))
    return g


def permutation_graph(n, seed):
    rng = random.Random(seed)
    cycle = list(range(n))
    rng.shuffle(cycle)
    succ = {cycle[i]: cycle[(i + 1) % n] for i in range(n)}
    while True:
        perm = list(range(n))
        rng.shuffle(perm)
        if all(perm[i] != succ[i] for i in range(n)):  # no two ports of a node lead to the same node
            break
    g = nx.DiGraph()
    for i in range(n):
        g.add_node(i, label='a')
    for i in range(n):
        g.add_edge(i, succ[i], port=0)
        g.add_edge(i, perm[i], port=1)
    return g


def marked_cycle(n):
    g = nx.DiGraph()
    for i in range(n):
        g.add_node(i, label='b' if i == 0 else 'a')
    for i in range(n):
        g.add_edge(i, (i + 1) % n, port=0)
    return g


def elapsed(f):
    start = time.perf_counter()
    f()
    return time.perf_counter() - start


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('family', choices=['random', 'cycle', 'permutation'])
    parser.add_argument('sizes', type=int, nargs='+', metavar='n')
    parser.add_argument('--reps', type=int, default=3, help='repetitions per size; the median is reported (default: 3)')
    parser.add_argument('--quadratic-max', type=int, default=4000,
                        help='largest n for which HO_all is run (default: 4000)')
    parser.add_argument('--merkle-max', type=int, default=None,
                        help='largest n for which HMg_ord is run (default: all sizes)')
    args = parser.parse_args()

    for n in args.sizes:
        acc = {}
        for r in range(args.reps):
            if args.family == "random":
                g = random_ordered(n, 1000 * n + r)
            elif args.family == "permutation":
                g = permutation_graph(n, 1000 * n + r)
            else:
                g = marked_cycle(n)
            acc.setdefault("scc", []).append(max(map(len, nx.strongly_connected_components(g))))
            acc.setdefault("HL", []).append(elapsed(lambda: local_hash(g)))
            acc.setdefault("HB", []).append(elapsed(lambda: local_hash(g, variant=V.BISIMULATION)))
            acc.setdefault("ord_local", []).append(elapsed(lambda: ordered_local_hash(g)))
            acc.setdefault("HMl_unord", []).append(elapsed(lambda: merkle_hash(g, LocalMH(V.UNFOLDING))))
            acc.setdefault("HMl_ord", []).append(elapsed(lambda: merkle_hash(g, OrderedLocalMH())))
            if n <= args.quadratic_max:
                acc.setdefault("HO_all", []).append(elapsed(lambda: {u: ordered_node_hash(g, u) for u in g}))
            if args.merkle_max is None or n <= args.merkle_max:
                acc.setdefault("HMg_ord", []).append(elapsed(lambda: merkle_hash(g, OrderedGlobalMH())))
        row = {"family": args.family, "n": n, **{k: round(statistics.median(v), 3) for k, v in acc.items()}}
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
