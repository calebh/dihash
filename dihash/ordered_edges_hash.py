import functools
from collections import defaultdict

from dihash.global_hash import _orbit_indices
from dihash.util import invert_list, hash_sha256, encode

def _port_successors(g, u):
    succ = sorted(((v, v_attr['port']) for (v, v_attr) in g[u].items()), key=lambda tup: tup[1])
    for (v, _) in succ:
        yield v

def _dfs(start, succ_iter):
    yield start

    discovered = set()
    discovered.add(start)

    stack = [succ_iter(start)]

    while len(stack) > 0:
        for node in stack[0]:
            if node not in discovered:
                yield node
                stack.append(succ_iter(node))
            break
        else:
            stack.pop()

def _ordered_edges_hash(g, node, string_hash_fun=hash_sha256):
    discovery_order = []
    succ_iter = functools.partial(_port_successors, g)
    for reachable_node in _dfs(node, succ_iter):
        discovery_order.append(reachable_node)

    labels = [g.nodes[n]['label'] for n in discovery_order]

    order_lookup = invert_list(discovery_order)

    out_seq = [[order_lookup[succ] for succ in succ_iter(node)] for node in discovery_order]

    return (string_hash_fun(encode((labels, out_seq))), discovery_order, order_lookup)

def ordered_edges_node_hash(g, node, string_hash_fun=hash_sha256):
    return _ordered_edges_hash(g, node, string_hash_fun=string_hash_fun)[0]

def ordered_edges_sc_global_hash(g, hash_nodes=False, string_hash_fun=hash_sha256):
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