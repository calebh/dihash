"""
Partition refinement algorithms used by local hashing.

States are numbered 0..n-1, keys[p] is a sortable value (the encoded label of p) and succ[p] lists the successors of
p. All functions return (block, num_blocks), where block[p] is the id of the block of state p and ids are numbered
0..num_blocks-1.
"""
from collections import defaultdict, deque

from .util import invert_list


def _initial_blocks(keys):
    """Blocks of states with equal keys, numbered in sorted order of the keys."""
    key_id = invert_list(sorted(set(keys)))
    block = [key_id[k] for k in keys]
    members = [[] for _ in key_id]
    position = [0] * len(keys)
    for (p, b) in enumerate(block):
        position[p] = len(members[b])
        members[b].append(p)
    return (block, members, position)


def _move(p, b, new, block, members, position):
    """Moves state p from block b to block new in O(1) time."""
    i = position[p]
    last = members[b][-1]
    members[b][i] = last
    position[last] = i
    members[b].pop()
    position[p] = len(members[new])
    members[new].append(p)
    block[p] = new


def canonical_count_partition(keys, succ):
    """
    Counting partition refinement (color refinement along outgoing edges). Computes the coarsest partition that refines\
    the partition by keys and is stable: any two states in one block have, for every block C, the same number of\
    successors in C, counted with multiplicity. Two states are in one block if and only if their unfoldings are\
    isomorphic.

    The block ids are canonical. Every decision depends only on block ids, block sizes, keys and successor counts, never\
    on the numbering of the states:
    - the initial blocks are numbered in sorted order of the keys;
    - splitters are processed first in, first out;
    - the blocks touched by a splitter are split in increasing order of their ids;
    - when a block splits, its states with no successor in the splitter keep the old id (if all states have a\
      successor in the splitter, those with the fewest keep it), and the other groups get new ids in increasing order\
      of their successor counts.
    Hence an isomorphism between two inputs (preserving keys and successor multisets) maps every block to the block\
    with the same id. If the stable partition is discrete, the block ids are a canonical order of the states.

    Splitting follows Cardon and Crochemore: a block that is waiting to be used as a splitter has all of its pieces\
    queued, and otherwise all pieces but a largest one are queued. Every state therefore belongs to a used splitter\
    O(log n) times, and the running time is O(m log^2 n) for n states and m edges (the extra log factor comes from the\
    sorting that makes the ids canonical).
    """
    n = len(succ)
    if n == 0:
        return ([], 0)
    (block, members, position) = _initial_blocks(keys)

    pred = [[] for _ in range(n)]
    for p in range(n):
        for q in succ[p]:
            pred[q].append(p)

    worklist = deque(range(len(members)))
    in_worklist = [True] * len(members)

    while worklist:
        splitter = worklist.popleft()
        in_worklist[splitter] = False

        # Number of successors in the splitter (as it is now) of every state that has one
        count = defaultdict(int)
        for q in members[splitter]:
            for p in pred[q]:
                count[p] += 1

        touched = defaultdict(list)
        for p in count:
            touched[block[p]].append(p)

        for b in sorted(touched):
            marked = touched[b]
            groups = defaultdict(list)
            for p in marked:
                groups[count[p]].append(p)
            counts = sorted(groups)
            if len(marked) == len(members[b]):
                if len(counts) == 1:
                    continue
                counts = counts[1:]  # all states have a successor in the splitter: the fewest keep the old id
            pieces = [b]
            for c in counts:
                new = len(members)
                members.append([])
                in_worklist.append(False)
                for p in groups[c]:
                    _move(p, b, new, block, members, position)
                pieces.append(new)

            if in_worklist[b]:
                queue = pieces[1:]
            else:
                largest = max(pieces, key=lambda piece: (len(members[piece]), -piece))
                queue = [piece for piece in pieces if piece != largest]
            for piece in queue:
                if not in_worklist[piece]:
                    worklist.append(piece)
                    in_worklist[piece] = True

    return (block, len(members))


def bisimulation_partition(keys, succ):
    """
    The coarsest partition that refines the partition by keys and is stable for bisimulation: for any two blocks B and\
    C, either every state of B has a successor in C or none has. Two states are in one block if and only if they are\
    bisimilar. Uses the algorithm of Paige and Tarjan, which runs in O(m log n) time. The block ids are not canonical.
    """
    n = len(succ)
    if n == 0:
        return ([], 0)
    succ = [sorted(set(s)) for s in succ]

    # Paige-Tarjan needs an initial partition that is stable with respect to the set of all states, so states with
    # and without successors start in different blocks.
    (block, members, position) = _initial_blocks([(k, len(s) > 0) for (k, s) in zip(keys, succ)])

    # Edges, the edges into each state, and for each edge the counter of (source, compound block of the target).
    # A counter is a one-element list so that edges can share it.
    edge_source = []
    edges_into = [[] for _ in range(n)]
    edge_counter = []
    for p in range(n):
        counter = [len(succ[p])]
        for q in succ[p]:
            edges_into[q].append(len(edge_source))
            edge_source.append(p)
            edge_counter.append(counter)

    # Compound blocks: each is a list of blocks; compound_of[b] is the compound block containing block b
    compounds = [list(range(len(members)))]
    compound_of = [0] * len(members)
    to_process = [0] if len(members) > 1 else []
    queued = [len(members) > 1]

    def split(marked_states):
        """Splits every block with marked states into its marked and unmarked states."""
        touched = defaultdict(list)
        for p in marked_states:
            touched[block[p]].append(p)
        for (b, marked) in touched.items():
            if len(marked) == len(members[b]):
                continue
            new = len(members)
            members.append([])
            for p in marked:
                _move(p, b, new, block, members, position)
            s = compound_of[b]
            compound_of.append(s)
            compounds[s].append(new)
            if not queued[s]:
                queued[s] = True
                to_process.append(s)

    while to_process:
        s = to_process.pop()
        queued[s] = False
        if len(compounds[s]) < 2:
            continue
        # Remove a block with at most half of the states of the compound block (the smaller of its last two blocks, so
        # that removal takes O(1) time), and make it a compound block of its own
        blocks = compounds[s]
        if len(members[blocks[-2]]) < len(members[blocks[-1]]):
            (blocks[-2], blocks[-1]) = (blocks[-1], blocks[-2])
        b = blocks.pop()
        new_s = len(compounds)
        compounds.append([b])
        queued.append(False)
        compound_of[b] = new_s
        if len(compounds[s]) >= 2:
            queued[s] = True
            to_process.append(s)

        # Count the successors in b of every predecessor of b
        count_b = defaultdict(int)
        counter_s = {}
        b_edges = []
        for q in members[b]:
            for e in edges_into[q]:
                p = edge_source[e]
                count_b[p] += 1
                counter_s[p] = edge_counter[e]
                b_edges.append(e)

        # Refine with respect to b, then with respect to s \ b: states whose successors in s all lie in b
        split(list(count_b))
        split([p for p in count_b if count_b[p] == counter_s[p][0]])

        # Update the counters: edges into b now count towards the new compound block
        counter_b = {p: [c] for (p, c) in count_b.items()}
        for e in b_edges:
            p = edge_source[e]
            edge_counter[e][0] -= 1
            edge_counter[e] = counter_b[p]

    return (block, len(members))
