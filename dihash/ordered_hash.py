import functools
from collections import defaultdict, deque

import networkx as nx

from dihash.global_hash import _orbit_indices
from dihash.util import invert_list, hash_sha256, encode

def _port_successors(g, u):
    """
    Yields the successors of u in the order of the 'port' attributes of the outgoing edges. Works for DiGraph and for\
    MultiDiGraph, where a node may link to the same target more than once (with different ports).
    """
    succ = []
    for (_, v, port) in g.out_edges(u, data='port'):
        if port is None:
            raise ValueError(f"Edge ({u}, {v}) has no 'port' attribute")
        succ.append((v, port))
    succ.sort(key=lambda tup: tup[1])
    for i in range(1, len(succ)):
        if succ[i - 1][1] == succ[i][1]:
            raise ValueError(f"Node {u} has two outgoing edges with port {succ[i][1]}; ports must be distinct")
    for (v, _) in succ:
        yield v

def _dfs(start, succ_iter):
    """
    Preorder (discovery order) of a depth-first search from start that explores the out-edges of each node in the\
    order given by succ_iter.
    """
    discovered = {start}
    yield start

    stack = [succ_iter(start)]

    while len(stack) > 0:
        for node in stack[-1]:
            if node not in discovered:
                discovered.add(node)
                yield node
                stack.append(succ_iter(node))
                break
        else:
            stack.pop()

def _ordered_edges_hash(g, node, string_hash_fun):
    discovery_order = []
    succ_iter = functools.partial(_port_successors, g)
    for reachable_node in _dfs(node, succ_iter):
        discovery_order.append(reachable_node)

    labels = [g.nodes[n]['label'] for n in discovery_order]

    order_lookup = invert_list(discovery_order)

    out_seq = [[order_lookup[succ] for succ in succ_iter(node)] for node in discovery_order]

    return (string_hash_fun(encode((labels, out_seq))), discovery_order, order_lookup)

def ordered_node_hash(g, node, string_hash_fun=hash_sha256):
    """
    Returns the hash of a node, solely determined by the reachable graph from that node. The graph is canonized\
    based on the DFS traversal order.

    :param g: An input directed graph, with edges having a label called 'port'. The outgoing edges of a node should\
    have non-duplicate port numbers.
    :param node: The node to compute the hash of.
    :param string_hash_fun: The string hashing function to use. Default is SHA-256
    :return:
    """
    return _ordered_edges_hash(g, node, string_hash_fun=string_hash_fun)[0]

def ordered_sc_global_hash(g, hash_nodes=False, string_hash_fun=hash_sha256):
    """
    Returns the hash of an entire strongly connected ordered graph, along with the hash of the nodes in the graph

    :param g: A strongly connected digraph. Edges in the graph should have a label called 'port', whose value is the port\
    identifier of that edge. The outgoing edges of a node should have non-duplicate port numbers. The port numbers\
    are used to order the DFS from the nodes.
    :param hash_nodes: If hash_nodes is True, the return value is (g_hash, node_hashes). Otherwise only the graph hash\
    is returned
    :param string_hash_fun: The string hashing function to use. Default is SHA-256
    :return: If hash_nodes is True, returns a tuple of (g_hash, node_hashes). Otherwise returns only the hash of the\
    entire strongly connected graph.
    """
    if not nx.is_strongly_connected(g):
        raise AssertionError("Input graph is not strongly connected")

    g_hash = None
    canon_order_lookup = dict()

    orbits = defaultdict(list)

    for n in g.nodes:
        (n_hash, _, order_lookup) = _ordered_edges_hash(g, n, string_hash_fun=string_hash_fun)

        if hash_nodes:
            orbits[n_hash].append(n)

        if g_hash is None or n_hash < g_hash:
            g_hash = n_hash
            canon_order_lookup = order_lookup

    if not hash_nodes:
        return g_hash
    else:
        orbit_partition = list(orbits.values())
        orbit_mapping = _orbit_indices(canon_order_lookup, orbit_partition)

        node_hashes = dict()
        for n in g.nodes:
            node_hashes[n] = string_hash_fun(encode((orbit_mapping[n], g_hash)))

        return (g_hash, node_hashes)


# --------------------------------------------------------------------------------------------------------------------
# Ordered local hashing
#
# An ordered graph is a partial deterministic automaton: the states are the nodes, and the letter k leads from a node
# to its k-th successor in port order. Two nodes have isomorphic ordered unfoldings if and only if they are equivalent
# states of this automaton whose outputs are (label, out-degree), so the equivalence classes are computed by DFA
# minimization (Hopcroft's algorithm) in O(m log n) time, independently of how deep the graph is.
# --------------------------------------------------------------------------------------------------------------------

def _ordered_lists(g):
    """
    Converts an ordered NetworkX graph into lists: (nodes, labels, out), where out[i] lists the indices of the\
    successors of nodes[i] in port order (with repetitions for repeated links).
    """
    nodes = list(g.nodes)
    index = invert_list(nodes)
    labels = [g.nodes[n]['label'] for n in nodes]
    out = [[index[v] for v in _port_successors(g, n)] for n in nodes]
    return (nodes, labels, out)

def _canonical_partition(keys, out):
    """
    Hopcroft-style partition refinement for the partial deterministic automaton with states 0..n-1, where letter k\
    leads from state p to out[p][k]. Computes the coarsest partition that refines the partition by (keys[p],\
    len(out[p])) and is stable: states in one block have their k-th successors in one block, for every k.

    The block ids are canonical: every decision depends only on block ids, block sizes, letters and sets of states,\
    never on the numbering of the states. Hence an isomorphism between two automata (preserving keys and successor\
    order) maps the blocks of one to the blocks of the other with the same ids. Block ids are numbered from 0.

    Every initial block is processed as a splitter and transitions are deterministic, so Hopcroft's "process the\
    smaller half" rule remains valid although some letters are undefined in some states (the automaton is partial).\
    Separating states by out-degree from the start is not needed for correctness, but saves work. Running time is\
    O(m log^2 n) for n states and m transitions (the extra log factor comes from visiting split blocks in id order).

    :return: (block, num_blocks), where block[p] is the id of the block of state p.
    """
    n = len(out)
    if n == 0:
        return ([], 0)

    # Initial blocks, numbered in sorted order of (key, out-degree)
    initial = [(keys[p], len(out[p])) for p in range(n)]
    initial_id = invert_list(sorted(set(initial)))
    block = [initial_id[k] for k in initial]
    members = [[] for _ in initial_id]
    position = [0] * n
    for p in range(n):
        position[p] = len(members[block[p]])
        members[block[p]].append(p)

    # Inverse transitions: inv[q] lists the pairs (p, k) with out[p][k] == q
    inv = [[] for _ in range(n)]
    for p in range(n):
        for (k, q) in enumerate(out[p]):
            inv[q].append((p, k))

    worklist = deque(range(len(members)))
    in_worklist = [True] * len(members)

    while worklist:
        splitter = worklist.popleft()
        in_worklist[splitter] = False

        # Predecessors of the splitter as it is now, grouped by letter
        predecessors = defaultdict(list)
        for q in members[splitter]:
            for (p, k) in inv[q]:
                predecessors[k].append(p)

        for k in sorted(predecessors):
            touched = defaultdict(list)
            for p in predecessors[k]:
                touched[block[p]].append(p)
            # Split blocks in order of their ids; the marked states form the new block
            for b in sorted(touched):
                marked = touched[b]
                if len(marked) == len(members[b]):
                    continue
                new = len(members)
                members.append([])
                in_worklist.append(False)
                for p in marked:
                    # Remove p from block b in O(1) by swapping it with the last member
                    i = position[p]
                    last = members[b][-1]
                    members[b][i] = last
                    position[last] = i
                    members[b].pop()
                    position[p] = len(members[new])
                    members[new].append(p)
                    block[p] = new
                if in_worklist[b]:
                    worklist.append(new)
                    in_worklist[new] = True
                else:
                    smaller = new if len(members[new]) <= len(members[b]) else b
                    worklist.append(smaller)
                    in_worklist[smaller] = True

    return (block, len(members))

def _quotient_lists(labels, keys, out, block, num_blocks):
    """
    The quotient automaton: one state per block, with the label of any member and the blocks of its successors.
    """
    representative = [None] * num_blocks
    for p in range(len(out)):
        if representative[block[p]] is None:
            representative[block[p]] = p
    q_labels = [labels[r] for r in representative]
    q_keys = [keys[r] for r in representative]
    q_out = [[block[t] for t in out[r]] for r in representative]
    return (q_labels, q_keys, q_out)

def _sc_local_hash_lists(labels, out, string_hash_fun):
    """
    Ordered local component hash of a strongly connected ordered graph given as lists (see _ordered_lists). Returns\
    (g_hash, node_hashes) with node_hashes a list indexed like labels.
    """
    keys = [encode(label) for label in labels]
    # Stage 1: minimize. block[p] is the class of p, i.e. its node in the minimal quotient
    (block, num_blocks) = _canonical_partition(keys, out)
    (q_labels, q_keys, q_out) = _quotient_lists(labels, keys, out, block, num_blocks)
    # Stage 2: canonical refinement of the quotient. The quotient is minimal, so the partition is discrete and its
    # canonical block ids are a canonical order of the quotient's nodes
    (canon_index, num_canon) = _canonical_partition(q_keys, q_out)
    if num_canon != num_blocks:
        raise AssertionError("Refinement of a minimal automaton is not discrete - this should be impossible")
    order = [None] * num_blocks
    for c in range(num_blocks):
        order[canon_index[c]] = c
    canon_labels = [q_labels[c] for c in order]
    canon_out = [[canon_index[t] for t in q_out[c]] for c in order]
    g_hash = string_hash_fun(encode((canon_labels, canon_out)))
    node_hashes = [string_hash_fun(encode((canon_index[block[p]], g_hash))) for p in range(len(out))]
    return (g_hash, node_hashes)

def ordered_sc_local_hash(g, string_hash_fun=hash_sha256):
    """
    Computes the ordered local hash of a strongly connected ordered graph, along with the hashes of its nodes. Two\
    nodes (in the same graph or in different graphs) receive the same hash if and only if their ordered unfoldings\
    are isomorphic, i.e. if they cannot be told apart by following outgoing edges by their position. The graph hash is\
    the hash of the minimal quotient (the graph obtained by merging all nodes with equal hashes), so two strongly\
    connected graphs have the same graph hash if and only if some node of one has the same hash as some node of the\
    other. Runs in O(m log^2 n) time, plus the cost of hashing.

    :param g: A strongly connected digraph (DiGraph or MultiDiGraph). Each node should have a 'label' entry in its node\
    attribute dictionary, and each edge a 'port' entry. The outgoing edges of a node are ordered by port, and the\
    ports of the outgoing edges of a node must be distinct.
    :param string_hash_fun: The string hashing function to use. Default is SHA-256
    :return: A tuple (g_hash, node_hashes), where node_hashes is a dictionary mapping nodes to their hashes.
    """
    if not nx.is_strongly_connected(g):
        raise AssertionError("Input graph is not strongly connected")
    (nodes, labels, out) = _ordered_lists(g)
    (g_hash, node_hashes) = _sc_local_hash_lists(labels, out, string_hash_fun)
    return (g_hash, {n: h for (n, h) in zip(nodes, node_hashes)})

# Marks an edge that stays inside its strongly connected component. It is encoded as "()", which differs from the
# encoding of every string, and therefore from every hash.
_INTERNAL = ()

def ordered_local_hash(g, string_hash_fun=hash_sha256):
    """
    Hashes every node of an ordered graph by its ordered unfolding. Two nodes (in the same graph or in different\
    graphs) receive the same hash if and only if their ordered unfoldings are isomorphic, i.e. if they cannot be told\
    apart by following outgoing edges by their position.

    The graph is first minimized as a deterministic automaton. On the minimal quotient, the ordered local Merkle hash\
    (see OrderedLocalMH in merkle_hash.py) distinguishes exactly the nodes with different ordered unfoldings, so each\
    strongly connected component of the quotient is serialized only once. Runs in O(m log^2 n) time, plus the cost of\
    hashing.

    :param g: A digraph (DiGraph or MultiDiGraph). Each node should have a 'label' entry in its node attribute\
    dictionary, and each edge a 'port' entry. The outgoing edges of a node are ordered by port, and the ports of the\
    outgoing edges of a node must be distinct.
    :param string_hash_fun: The string hashing function to use. Default is SHA-256
    :return: A dictionary mapping nodes to their hashes.
    """
    (nodes, labels, out) = _ordered_lists(g)
    keys = [encode(label) for label in labels]
    (block, num_blocks) = _canonical_partition(keys, out)
    (q_labels, _, q_out) = _quotient_lists(labels, keys, out, block, num_blocks)

    quotient = nx.DiGraph()
    quotient.add_nodes_from(range(num_blocks))
    quotient.add_edges_from((c, t) for c in range(num_blocks) for t in q_out[c])
    cond = nx.condensation(quotient)

    q_hash = [None] * num_blocks
    for scc in reversed(list(nx.topological_sort(cond))):
        component = sorted(cond.nodes[scc]['members'])
        inside = invert_list(component)
        # Relabel with the hashes of the external successors, and a marker for internal ones, in port order
        relabeled = [(q_labels[c], [_INTERNAL if t in inside else q_hash[t] for t in q_out[c]]) for c in component]
        internal_out = [[inside[t] for t in q_out[c] if t in inside] for c in component]
        (_, component_hashes) = _sc_local_hash_lists(relabeled, internal_out, string_hash_fun)
        for (c, h) in zip(component, component_hashes):
            q_hash[c] = h

    return {n: q_hash[block[p]] for (p, n) in enumerate(nodes)}
