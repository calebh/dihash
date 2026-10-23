from gen_graphs import *

def test_hash_graph():
    g1 = nx.DiGraph()
    g1.add_node(0)
    g1.add_node(1)
    g1.add_node(2)
    g1.nodes[0]['label'] = 'a'
    g1.nodes[1]['label'] = 'a'
    g1.nodes[2]['label'] = 'a'

    g1.add_edge(0, 1)
    g1.add_edge(1, 2)
    g1.add_edge(2, 0)

    g2 = nx.DiGraph()
    g2.add_node(0)
    g2.add_node(1)
    g2.add_node(2)
    g2.add_node(3)
    g2.nodes[0]['label'] = 'a'
    g2.nodes[1]['label'] = 'a'
    g2.nodes[2]['label'] = 'a'
    g2.nodes[3]['label'] = 'a'

    g2.add_edge(0, 1)
    g2.add_edge(1, 2)
    g2.add_edge(2, 3)
    g2.add_edge(3, 0)

    # Nodes in the same orbit hash to the same values
    (hash_1, node_hashes_1) = dihash.global_hash(g1, hash_nodes=True)
    assert(node_hashes_1[0] == node_hashes_1[1])
    assert(node_hashes_1[0] == node_hashes_1[2])

    (hash_2, node_hashes_2) = dihash.global_hash(g2, hash_nodes=True)

    assert(node_hashes_2[0] == node_hashes_2[1])
    assert(node_hashes_2[0] == node_hashes_2[2])
    assert(node_hashes_2[0] == node_hashes_2[3])

    assert(node_hashes_1[0] != node_hashes_2[0])

    print("test_graph_hash passed")

def test_iso_duplicate_removal():
    for num_nodes in range(1, 4):
        assert(len(generate_graphs(num_nodes)) == len(generate_graphs_nx_iso(num_nodes)))

    print("test_iso_duplicate_removal passed")

if __name__ == "__main__":
    test_hash_graph()
    test_iso_duplicate_removal()

    print("All tests passed!")
