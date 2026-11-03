"""
Granularity paragraph of the paper: how many classes the different equivalences induce on small random digraphs.

Hashes random unlabeled digraphs with 12 nodes and 18 randomly drawn edges (duplicates discarded) and prints, as JSON,
the average number of distinct hash values per graph for the global node hash (orbits), the global and local Merkle
hashes, the local hash (unfolding classes) and the bisimulation hash.

Usage: python experiments/granularity.py [--graphs 400] [--seed 5]
The paper uses the defaults (results/granularity.json).
"""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import networkx as nx

import dihash
from dihash.local_hash import local_hash, LocalHashVariant as V
from dihash.merkle_hash import merkle_hash, GlobalMH, LocalMH

NODES, EDGES = 12, 18

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--graphs', type=int, default=400, help='number of random graphs (default: 400)')
parser.add_argument('--seed', type=int, default=5, help='random seed (default: 5)')
args = parser.parse_args()

rng = random.Random(args.seed)
total = {}
for _ in range(args.graphs):
    g = nx.DiGraph()
    for i in range(NODES):
        g.add_node(i, label='a')
    for _ in range(EDGES):
        g.add_edge(rng.randrange(NODES), rng.randrange(NODES))
    hashes = {
        "orbits": dihash.global_hash(g, hash_nodes=True)[1],
        "merkle_glob": merkle_hash(g, GlobalMH())[2],
        "merkle_loc": merkle_hash(g, LocalMH(V.UNFOLDING))[2],
        "local": local_hash(g),
        "bisim": local_hash(g, variant=V.BISIMULATION),
    }
    for k, h in hashes.items():
        total[k] = total.get(k, 0) + len(set(h.values()))
print(json.dumps({k: round(v / args.graphs, 2) for k, v in total.items()}))
