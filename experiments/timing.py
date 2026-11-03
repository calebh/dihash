"""
Scaling table of the paper (Table "Time in seconds to hash all nodes of a graph with n nodes").

Times the local hashes, the local Merkle hashes and the quadratic ordered baselines on one family of ordered digraphs
and prints one JSON row per graph size with the median time in seconds of each hash over the repetitions.

  random  two labels and 2n randomly drawn edges, duplicates discarded, ports in order of insertion;
          a new random graph is drawn for every repetition
  cycle   the directed n-cycle in which node 0 has a different label (a single deterministic graph)

Usage: python experiments/timing.py {random,cycle} [--reps R] [--quadratic-max N] n [n ...]

The paper's table was produced with
  python experiments/timing.py random --reps 3 1000 4000 16000 64000   (results/timing_random.jsonl)
  python experiments/timing.py cycle  --reps 1 1000 4000 16000 64000   (results/timing_cycle.jsonl)

Columns: scc = size of the largest strongly connected component; HL = local hash; HB = bisimulation hash;
ord_local = ordered local hash; HMl_unord / HMl_ord = local Merkle hash of the graph as an unordered / ordered graph;
HO_all = ordered node hash of every node; HMg_ord = global Merkle hash of the ordered graph. The last two are
quadratic and are only run for n <= --quadratic-max.
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
    parser.add_argument('family', choices=['random', 'cycle'])
    parser.add_argument('sizes', type=int, nargs='+', metavar='n')
    parser.add_argument('--reps', type=int, default=3, help='repetitions per size; the median is reported (default: 3)')
    parser.add_argument('--quadratic-max', type=int, default=4000,
                        help='largest n for which the quadratic baselines are run (default: 4000)')
    args = parser.parse_args()

    for n in args.sizes:
        acc = {}
        for r in range(args.reps):
            g = random_ordered(n, 1000 * n + r) if args.family == "random" else marked_cycle(n)
            acc.setdefault("scc", []).append(max(map(len, nx.strongly_connected_components(g))))
            acc.setdefault("HL", []).append(elapsed(lambda: local_hash(g)))
            acc.setdefault("HB", []).append(elapsed(lambda: local_hash(g, variant=V.BISIMULATION)))
            acc.setdefault("ord_local", []).append(elapsed(lambda: ordered_local_hash(g)))
            acc.setdefault("HMl_unord", []).append(elapsed(lambda: merkle_hash(g, LocalMH(V.UNFOLDING))))
            acc.setdefault("HMl_ord", []).append(elapsed(lambda: merkle_hash(g, OrderedLocalMH())))
            if n <= args.quadratic_max:
                acc.setdefault("HO_all", []).append(elapsed(lambda: {u: ordered_node_hash(g, u) for u in g}))
                acc.setdefault("HMg_ord", []).append(elapsed(lambda: merkle_hash(g, OrderedGlobalMH())))
        row = {"family": args.family, "n": n, **{k: round(statistics.median(v), 3) for k, v in acc.items()}}
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
