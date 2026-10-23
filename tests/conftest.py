import os
import sys

# Allow the test modules to import their helpers (gen_graphs, brute_force) and the dihash package when run with
# `python -m pytest` from the repository root.
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (HERE, ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)
