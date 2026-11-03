# Experiments

Scripts that produce the numbers in the Experimental Results section of the paper (`papers/soda/dihash.tex`). They
run against the library in this repository, not an installed copy, and need `pynauty` and `networkx` (install pynauty
with `pip install --no-binary pynauty pynauty`). Run them from any directory; each prints JSON to standard output.

| Script | Paper | Command used for the paper | Output in `results/` |
| --- | --- | --- | --- |
| `validate.py` | Validation table | `python experiments/validate.py` | `validation.json` |
| `timing.py` | Scaling table | `python experiments/timing.py random --reps 3 1000 4000 16000 64000` | `timing_random.jsonl` |
| | | `python experiments/timing.py cycle --reps 1 1000 4000 16000 64000` | `timing_cycle.jsonl` |
| | | `python experiments/timing.py permutation --reps 3 --merkle-max 4000 1000 4000 16000 64000` | `timing_permutation.jsonl` |
| `granularity.py` | Granularity paragraph | `python experiments/granularity.py` | `granularity.json` |

## validate.py

Compares every hash with the brute-force decision procedures in `tests/brute_force.py` on 3000 random pairs of
labeled graphs per scheme (1–6 nodes; see `brute_force.random_pair`) and counts the node pairs that were compared. The
script stops with an `AssertionError` at the first disagreement. The counts depend only on the random seeds, so a rerun
reproduces `validation.json` exactly. It takes a few minutes. Use `--trials` for a quicker run.

The keys correspond to the rows of the table: `global_graph`, `global_node`; `local`, `bisim`, `comp` and `comp_bisim`
(the local hash, the bisimulation hash and the two local component hashes); `ord_node`, `ord_local`, `ord_sc_global`
and `ord_sc_local`; `merkle_glob`, `merkle_loc` and `merkle_bisim`; `ord_merkle_glob` and `ord_merkle_loc`.

## timing.py

Times each hash on ordered random digraphs, on a marked directed cycle, or on permutation graphs (the worst case of
`ordered_sc_global_hash`, in which every port permutes the nodes) and reports the median in seconds. `HO_all` is
quadratic and runs only up to `--quadratic-max` nodes (4000 by default); `HMg_ord` runs up to `--merkle-max` nodes (all
sizes by default; 4000 for the permutation graphs, where it is quadratic). Sizes that are not run appear as dashes in
the table. The graphs, and hence the `scc` column, depend only on the seeds. The times depend on the machine; the
paper's numbers were measured with Python 3.13 on one core of an Intel Xeon at 2.1 GHz. The runs at the sizes above
took about 7 minutes for the random graphs, 2 minutes for the cycle and 17 minutes for the permutation graphs, almost
all of it in the quadratic columns at n = 4000.

## granularity.py

Counts the distinct hash values per graph for five equivalences on 400 random unlabeled digraphs with 12 nodes and 18
drawn edges, and reports the averages. A run takes about a second and reproduces `granularity.json` exactly.
