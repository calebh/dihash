import time
import random
import networkx as nx
import dihash
import signal
import multiprocessing
import statistics
import math

def run_with_limited_time(func, args, kwargs, time):
    """Runs a function with time limit

    :param func: The function to run
    :param args: The functions args, given as tuple
    :param kwargs: The functions keywords, given as dict
    :param time: The time limit in seconds
    :return: True if the function ended successfully. False if it was terminated.
    """
    p = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
    p.start()
    p.join(time)
    if p.is_alive():
        p.terminate()
        return False
    return True

def generate_graph(trial_i, compute_graph_size):
    (num_nodes, num_edges) = compute_graph_size(trial_i)
    g = nx.gnm_random_graph(num_nodes, num_edges, directed=True)
    while not nx.is_weakly_connected(g):
        (num_nodes, num_edges) = compute_graph_size(trial_i)
        g = nx.gnm_random_graph(num_nodes, num_edges, directed=True)
    for n in g.nodes():
        g.nodes[n]['label'] = ''
    return g

manager = multiprocessing.Manager()

def benchmark(start_trial, num_trials, compute_graph_size, output_file, timeout=10):
    num_trials_per_run = 100

    with open(output_file, "w") as f:
        for trial_i in range(start_trial, num_trials):
            print("Running trial " + str(trial_i))

            def run_hash(iter_dict, ret_duration):
                while iter_dict['completed'] < num_trials_per_run:
                    g = generate_graph(trial_i, compute_graph_size)
                    start = time.time()
                    dihash.hash_graph(g, hash_nodes=False, apply_quotient=False)
                    end = time.time()
                    iter_dict['completed'] += 1
                    ret_duration.append(end - start)

            finished = False

            iter_dict = manager.dict()
            iter_dict['completed'] = 0
            iter_dict['i'] = 0
            ret_durations = manager.list()

            while not finished:
                finished = run_with_limited_time(run_hash, [iter_dict, ret_durations], {}, timeout)
                if not finished:
                    print("timeout")

            durations = list(ret_durations)

            f.write(str(trial_i))
            f.write(',')
            f.write(str(statistics.median(durations)))
            f.write('\n')

def nodes_compute_graph_size(trial_i):
    num_nodes = trial_i + 1
    num_edges = random.randint(num_nodes - 1, num_nodes ** 2)
    return (num_nodes, num_edges)

def edges_compute_graph_size(trial_i):
    num_edges = trial_i + 1
    min_num_nodes = math.ceil(math.sqrt(num_edges))
    max_num_nodes = num_edges + 1
    num_nodes = random.randint(min_num_nodes, max_num_nodes)
    return (num_nodes, num_edges)

benchmark(0, 1000, nodes_compute_graph_size, "num_nodes_benchmark.csv")