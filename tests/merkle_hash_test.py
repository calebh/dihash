import networkx as nx
import dihash
from dihash.merkle_hash import MerkleHashVariant

def test_merkle_hash_graph():
    g1 = nx.DiGraph()
    g1.add_node(0)
    g1.add_node(1)
    g1.add_node(2)
    g1.add_node(3)
    g1.add_node(4)
    g1.add_node(5)
    g1.add_node(6)

    g1.nodes[0]['label'] = 'a'
    g1.nodes[1]['label'] = 'a'
    g1.nodes[2]['label'] = 'a'
    g1.nodes[3]['label'] = 'a'
    g1.nodes[4]['label'] = 'a'
    g1.nodes[5]['label'] = 'a'
    g1.nodes[6]['label'] = 'a'

    g1.add_edge(0, 1)
    g1.add_edge(0, 2)

    g1.add_edge(1, 5)
    g1.add_edge(4, 6)

    g1.add_edge(1, 2)
    g1.add_edge(2, 1)
    g1.add_edge(2, 3)
    g1.add_edge(3, 2)
    g1.add_edge(3, 4)
    g1.add_edge(4, 3)

    (scc_hashes1, cond1, node_hashes1) = dihash.merkle_hash(g1, MerkleHashVariant.GLOBAL)

    assert(node_hashes1[1] == node_hashes1[4])
    assert(node_hashes1[2] == node_hashes1[3])
    assert(node_hashes1[5] == node_hashes1[6])

    g2 = nx.DiGraph()
    g2.add_node(0)
    g2.add_node(1)
    g2.add_node(2)
    g2.add_node(3)
    g2.add_node(4)
    g2.add_node(5)
    g2.add_node(6)

    g2.nodes[0]['label'] = 'a'
    g2.nodes[1]['label'] = 'a'
    g2.nodes[2]['label'] = 'a'
    g2.nodes[3]['label'] = 'a'
    g2.nodes[4]['label'] = 'a'
    g2.nodes[5]['label'] = 'a'
    g2.nodes[6]['label'] = 'a'

    g2.add_edge(0, 1)
    g2.add_edge(0, 3)

    g2.add_edge(1, 5)
    g2.add_edge(4, 6)

    g2.add_edge(1, 2)
    g2.add_edge(2, 1)
    g2.add_edge(2, 3)
    g2.add_edge(3, 2)
    g2.add_edge(3, 4)
    g2.add_edge(4, 3)

    (scc_hashes2, cond2, node_hashes2) = dihash.merkle_hash(g1, MerkleHashVariant.GLOBAL)

    assert(node_hashes2[1] == node_hashes2[4])
    assert(node_hashes2[2] == node_hashes2[3])
    assert(node_hashes2[5] == node_hashes2[6])

    assert(node_hashes1[0] == node_hashes2[0])
    assert(node_hashes1[1] == node_hashes2[1])
    assert(node_hashes1[2] == node_hashes2[2])
    assert(node_hashes1[5] == node_hashes2[5])

    for i in range(6):
        assert(scc_hashes1[cond1.graph['mapping'][i]] == scc_hashes2[cond2.graph['mapping'][i]])

    print("test_merkle_hash_graph passed")

def test_merkle_hash_graph2():
    g1 = nx.DiGraph()
    g1.add_node(0)
    g1.add_node(1)

    g1.add_edge(0, 1)
    g1.add_edge(1, 0)

    g1.nodes[0]['label'] = 'a'
    g1.nodes[1]['label'] = 'a'

    (scc_hashes1, cond1, node_hashes1) = dihash.merkle_hash(g1, MerkleHashVariant.LOCAL)

    assert(node_hashes1[0] == node_hashes1[1])

    g2 = nx.DiGraph()
    g2.add_node(0)

    g2.add_edge(0, 0)

    g2.nodes[0]['label'] = 'a'

    (scc_hashes2, cond2, node_hashes2) = dihash.merkle_hash(g2, MerkleHashVariant.LOCAL)

    assert(node_hashes1[0] == node_hashes2[0])

    g3 = nx.DiGraph()
    g3.add_node(0)

    g3.nodes[0]['label'] = 'a'

    (scc_hashes3, cond3, node_hashes3) = dihash.merkle_hash(g3, MerkleHashVariant.LOCAL)

    assert(node_hashes3[0] != node_hashes1[0])

    print("test_merkle_hash_graph2 passed")

test_merkle_hash_graph()
test_merkle_hash_graph2()

print("All tests passed!")