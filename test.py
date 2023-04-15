import networkx as nx
import dihash
import gen_graphs

def test_quotient():
    g1 = nx.DiGraph()
    g1.add_node(0)
    g1.add_node(1)
    g1.add_node(2)
    g1.add_node(3)
    g1.add_node(4)
    g1.add_node(5)
    g1.add_node(6)
    g1.add_node(7)
    g1.nodes[0]['label'] = 'a'
    g1.nodes[1]['label'] = 'a'
    g1.nodes[2]['label'] = 'a'
    g1.nodes[3]['label'] = 'a'
    g1.nodes[4]['label'] = 'a'
    g1.nodes[5]['label'] = 'a'
    g1.nodes[6]['label'] = 'a'
    g1.nodes[7]['label'] = 'a'

    g1.add_edge(0,1)
    g1.add_edge(0,2)
    g1.add_edge(1,3)
    g1.add_edge(2,3)
    g1.add_edge(3,0)
    g1.add_edge(0,4)
    g1.add_edge(0,5)
    g1.add_edge(4,6)
    g1.add_edge(5,7)
    g1.add_edge(6,0)
    g1.add_edge(7,0)

    (sigma2, g2) = dihash.quotient_graph(g1)

    expected2 = nx.MultiDiGraph()
    expected2.add_node(0)
    expected2.add_node(1)
    expected2.add_node(2)
    expected2.add_node(3)
    expected2.add_node(4)

    expected2.nodes[0]['label'] = 'a'
    expected2.nodes[1]['label'] = 'a'
    expected2.nodes[2]['label'] = 'a'
    expected2.nodes[3]['label'] = 'a'
    expected2.nodes[4]['label'] = 'a'

    expected2.add_edge(0,1)
    expected2.add_edge(0,1)
    expected2.add_edge(1,2)
    expected2.add_edge(2,0)
    expected2.add_edge(0,3)
    expected2.add_edge(0,3)
    expected2.add_edge(3,4)
    expected2.add_edge(4,0)

    assert(nx.is_isomorphic(g2, expected2))

    (sigma3, g3) = dihash.quotient_graph(g2)

    expected3 = nx.MultiDiGraph()
    expected3.add_node(0)
    expected3.add_node(1)
    expected3.add_node(2)

    expected3.nodes[0]['label'] = 'a'
    expected3.nodes[1]['label'] = 'a'
    expected3.nodes[2]['label'] = 'a'

    expected3.add_edge(0, 1)
    expected3.add_edge(0, 1)
    expected3.add_edge(0, 1)
    expected3.add_edge(0, 1)
    expected3.add_edge(1, 2)
    expected3.add_edge(2, 0)

    assert(nx.is_isomorphic(g3, expected3))

    (sigma4, g4) = dihash.quotient_fixpoint(g1)

    assert(nx.is_isomorphic(g4, expected3))

    print("test_quotient passed")

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

    expected_quotient = nx.DiGraph()
    expected_quotient.add_node(0)
    expected_quotient.nodes[0]['label'] = 'a'

    expected_quotient.add_edge(0, 0)

    (hash_1, node_hashes_1) = dihash.hash_graph(g1, apply_quotient=False)
    assert(node_hashes_1[0] == node_hashes_1[1])
    assert(node_hashes_1[0] == node_hashes_1[2])

    (hash_2, node_hashes_2) = dihash.hash_graph(g2, apply_quotient=False)

    assert(node_hashes_2[0] == node_hashes_2[1])
    assert(node_hashes_2[0] == node_hashes_2[2])
    assert(node_hashes_2[0] == node_hashes_2[3])

    assert(node_hashes_1[0] != node_hashes_2[0])

    assert(hash_1 != hash_2)

    (hash_3, node_hashes_3) = dihash.hash_graph(g1, apply_quotient=True)
    assert(node_hashes_3[0] == node_hashes_3[1])
    assert(node_hashes_3[0] == node_hashes_3[2])

    (hash_4, node_hashes_4) = dihash.hash_graph(g2, apply_quotient=True)
    assert(node_hashes_4[0] == node_hashes_4[1])
    assert(node_hashes_4[0] == node_hashes_4[2])
    assert(node_hashes_4[0] == node_hashes_4[3])

    assert(node_hashes_3[0] == node_hashes_4[0])
    assert(node_hashes_1[0] != node_hashes_3[0])
    assert(node_hashes_2[0] != node_hashes_4[0])

    assert(hash_3 == hash_4)

    (hash_5, node_hashes_5) = dihash.hash_graph(expected_quotient, apply_quotient=False)

    assert(node_hashes_3[0] == node_hashes_5[0])
    assert(hash_3 == hash_5)

    print("test_graph_hash passed")

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

    (scc_hashes1, cond1, node_hashes1) = dihash.merkle_hash_graph(g1, apply_quotient=False)

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

    (scc_hashes2, cond2, node_hashes2) = dihash.merkle_hash_graph(g1, apply_quotient=False)

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

def test_iso_duplicate_removal():
    for num_nodes in range(1, 4):
        assert(len(gen_graphs.generate_graphs(num_nodes)) == len(gen_graphs.generate_graphs_nx_iso(num_nodes)))

    print("test_iso_duplicate_removal passed")

def test_edge_encoding():
    # This example is what is shown in the nauty manual, section 14, Figure 3
    g = nx.DiGraph()
    g.add_node(1)
    g.add_node(2)
    g.add_node(3)
    g.add_node(4)
    g.nodes[1]['label'] = 'node_label'
    g.nodes[2]['label'] = 'node_label'
    g.nodes[3]['label'] = 'node_label'
    g.nodes[4]['label'] = 'node_label'
    g.add_edge(1,1)
    g.add_edge(1,2)
    g.add_edge(2,3)
    g.add_edge(3,1)
    g.add_edge(3,4)
    g.add_edge(4,3)
    g.add_edge(4,1)
    g.edges[(1,1)]['label'] = 'c-solid'
    g.edges[(1,2)]['label'] = 'a-dashed'
    g.edges[(2,3)]['label'] = 'c-solid'
    g.edges[(3,1)]['label'] = 'b-dashed-dotted'
    g.edges[(4,3)]['label'] = 'a-dashed'
    g.edges[(4,1)]['label'] = 'b-dashed-dotted'
    g.edges[(3,4)]['label'] = 'b-dashed-dotted'

    expected = nx.DiGraph()
    # Layer 0 is the lower layer in the example
    expected.add_node((0,1))
    expected.add_node((0,2))
    expected.add_node((0,3))
    expected.add_node((0,4))
    # Layer 1 is the upper layer in the example
    expected.add_node((1,1))
    expected.add_node((1,2))
    expected.add_node((1,3))
    expected.add_node((1,4))

    # Connect the nodes up in layer 0
    expected.add_edge((0,1),(0,1))
    expected.add_edge((0,1),(0,2))
    expected.add_edge((0,2),(0,3))
    expected.add_edge((0,4),(0,3))

    # Connect the nodes up in layer 1
    expected.add_edge((1,1),(1,1))
    expected.add_edge((1,2),(1,3))
    expected.add_edge((1,3),(1,4))
    expected.add_edge((1,3),(1,1))
    expected.add_edge((1,4),(1,1))

    # Make the vertical threads
    expected.add_edge((0,1),(1,1))
    expected.add_edge((0,2),(1,2))
    expected.add_edge((0,3),(1,3))
    expected.add_edge((0,4),(1,4))

    (g_prime, _) = dihash.edge_labeled_digraph_to_digraph(g)

    assert(frozenset(g_prime.nodes()) == frozenset(expected.nodes()))
    assert(frozenset(g_prime.edges()) == frozenset(expected.edges()))
    assert(nx.is_isomorphic(g_prime, expected))

    print("test_edge_encoding passed")

def test_hash_graph_node_set():
    g = nx.DiGraph()
    g.add_node(1)
    g.add_node(2)
    g.add_node(3)
    g.add_node(4)

    g.nodes[1]['label'] = 'node_label'
    g.nodes[2]['label'] = 'node_label'
    g.nodes[3]['label'] = 'node_label'
    g.nodes[4]['label'] = 'node_label'

    g.add_edge(1, 2)
    g.add_edge(2, 1)
    g.add_edge(2, 3)
    g.add_edge(3, 2)
    g.add_edge(3, 4)
    g.add_edge(4, 3)
    g.add_edge(4, 1)
    g.add_edge(1, 4)

    (g_hash1, node_hashes1) = dihash.hash_graph_node_set(g, {1, 3})
    (g_hash2, node_hashes2) = dihash.hash_graph_node_set(g, {2, 4})

    assert(g_hash1 == g_hash2)
    assert(node_hashes1[1] == node_hashes1[3])
    assert(node_hashes2[2] == node_hashes2[4])
    assert(node_hashes1[1] == node_hashes2[2])

    (g_hash3, node_hashes3) = dihash.hash_graph_node_set(g, {1, 2})
    (g_hash4, node_hashes4) = dihash.hash_graph_node_set(g, {2, 3})

    assert(g_hash3 == g_hash4)
    assert(g_hash3 != g_hash1)
    assert(node_hashes3[1] == node_hashes3[2])
    assert(node_hashes4[2] == node_hashes4[3])
    assert(node_hashes3[1] == node_hashes4[2])
    assert(node_hashes1[1] != node_hashes3[1])

    g2 = nx.DiGraph()
    g2.add_node(1)
    g2.add_node(2)
    g2.add_node(3)
    g2.add_node(4)

    g2.nodes[1]['label'] = 'node_label'
    g2.nodes[2]['label'] = 'node_label'
    g2.nodes[3]['label'] = 'node_label'
    g2.nodes[4]['label'] = 'node_label'

    g2.add_edge(1, 2)
    g2.add_edge(2, 3)
    g2.add_edge(3, 4)
    g2.add_edge(4, 1)

    (g_hash5, node_hashes5) = dihash.hash_graph_node_set(g2, {1, 2})
    (g_hash6, node_hashes6) = dihash.hash_graph_node_set(g2, {3, 4})

    assert(g_hash5 == g_hash6)
    assert(node_hashes5[1] != node_hashes5[2])
    assert(node_hashes6[3] != node_hashes6[4])
    assert(node_hashes5[1] == node_hashes6[3])
    assert(node_hashes5[2] == node_hashes6[4])

    print("test_hash_graph_node_set passed")

test_quotient()
test_hash_graph()
test_merkle_hash_graph()
test_iso_duplicate_removal()
test_edge_encoding()
test_hash_graph_node_set()

print("All tests passed!")