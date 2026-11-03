# Experiments

Scripts that produce the numbers in the Experimental Results section of the paper (`papers/soda/dihash.tex`). They
run against the library in this repository, not an installed copy, and need `pynauty` and `networkx` (install pynauty
with `pip install --no-binary pynauty pynauty`). Run them from any directory; each prints JSON to standard output.

| Script | Paper | Command used for the paper | Output in `results/` |
| --- | --- | --- | --- |
| `validate.py` | Validation table | `python experiments/validate.py` | `validation.json` |
| `timing.py` | Scaling table | `python experiments/timing.py random --reps 3 1000 4000 16000 64000` | `timing_random.jsonl` |
| | | `python experiments/timing.py cycle --reps 1 1000 4000 16000 64000` | `timing_cycle.jsonl` |
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

Times each hash on ordered random digraphs or on a marked directed cycle and reports the median in seconds. The
quadratic baselines (`HO_all`, `HMg_ord`) run only up to `--quadratic-max` nodes (4000 by default); larger sizes appear
as dashes in the table. The graphs, and hence the `scc` column, depend only on the seeds. The times depend on the
machine; the paper's numbers were measured with Python 3.13 on one core of an Intel Xeon at 2.8 GHz. The full runs at
the sizes above took about 5 minutes for the cycle and 15 minutes for the random graphs, almost all of it in the
quadratic baselines at n = 4000.

## granularity.py

Counts the distinct hash values per graph for five equivalences on 400 random unlabeled digraphs with 12 nodes and 18
drawn edges, and reports the averages. A run takes about a second and reproduces `granularity.json` exactly.
