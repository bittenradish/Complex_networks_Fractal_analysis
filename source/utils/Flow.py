import graph_tool.all as gt
import numpy as np
import os
import json
import glob
import subprocess
import shlex

__all__ = ['analysis_folder', 
           'is_weight_type_supported', 
           'has_parallel_edges', 
           'simplify_graph_with_weights', 
           'prepare_folder',
           'directed_to_undirected_sum_weights',
           'saveTSV',
           'get_latest_output_json',
           'save_json',
           'run_box_covering',
           'start_box_covering_pipeline'
           ]

# Flow Variables

analysis_folder = "./analysis_data/"

# Flow functions

## Box covering pipeline functions


def saveTSV(filePath, graph):
    # fmt='%d' ensures ids are written as integers
    np.savetxt(filePath, graph.get_edges()[:, :2], fmt='%d', delimiter='\t')


def get_latest_output_json():
    list_of_files = glob.glob('./graph_sketch_fractality/jlog/*')
    latest_file = max(list_of_files, key=os.path.getctime)

    f = open(latest_file, "r").read()
    json_file = json.loads(f)

    return json_file


def save_json(path, json_file):
    with open(path, "w") as outfile:
        json.dump(json_file, outfile)


def run_box_covering(**kwargs):
    
    # Default arguments of the method:
    default_args = {'type': 'gen', 'graph': "flower 1000 1 2", 'method': 'sketch', 'alpha': '1', 'least_coverage': '1',
           'sketch_k': '128', 'multipass': '10000', 'rad_min': '1', 'rad_max': '30', 'random_seed': '114514'}
    
    options = ""
    
    for key in kwargs:
        default_args[key] = kwargs[key]
        
    if default_args['type'] == 'gen':
        a = default_args['graph']
        default_args['graph'] = f'"{a}"'
            
    for key in default_args:
        options += f" -{key}={default_args[key]}"
        
    subprocess.run(shlex.split(f"./bin/box_cover {options}"), cwd='./graph_sketch_fractality')


def start_box_covering_pipeline(graph, folder_path, is_mst):
    suffix = "mst" if is_mst else "graph"

    tsv_path = f"{folder_path}/{suffix}.tsv"
    saveTSV(tsv_path, graph)

    run_box_covering(type="tsv", graph=f".{tsv_path}")

    json = get_latest_output_json()
    save_json(f"{folder_path}/box_{suffix}_result.json", json)


## Graph preparation functions


def prepare_folder(graph_name):
    safe_graph_name = graph_name.replace('/', '__')
    path = f"{analysis_folder}{safe_graph_name}"
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def is_weight_type_supported(type):
    supported_types = ['int16_t', 'int32_t', 'int64_t', 'float', 'double', 'long double']
    return type in supported_types


def has_parallel_edges(g: gt.Graph) -> bool:
    #Edges -> Numpy array [source, target]
    edges = g.get_edges()[:, :2]
    
    if edges.shape[0] == 0:
        return False

    if not g.is_directed():
        edges.sort(axis=1)
        

    # If the number of unique rows is less than total rows, duplicates exist.
    unique_edges = np.unique(edges, axis=0)
    
    return len(unique_edges) < len(edges)


def simplify_graph_with_weights(graph: gt.Graph, weight_name = None, inplace: bool = False) -> tuple[gt.Graph, gt.EdgePropertyMap]:
    processed_weight_map: gt.EdgePropertyMap
    
    if inplace:
        g = graph
    else:
        g = graph.copy()

    # Scenario: Specific weight property provided
    if isinstance(weight_name, str):
        if weight_name not in g.ep:
            raise ValueError(f"Edge property '{weight_name}' not found in the graph. Cannot sum non-existent weights.")
            
        existing_weights_to_sum = g.ep[weight_name] 
        
        summed_map = gt.contract_parallel_edges(g, existing_weights_to_sum)
        
        g.ep[weight_name] = summed_map
        processed_weight_map = summed_map

    # Scenario: No weight provided (Default to counting multiplicity or summing 'weight')
    else:
        # If 'weight' exists and is numeric, sum it. Otherwise, count edges.
        if 'weight' in g.ep and is_weight_type_supported(g.ep['weight'].value_type()):
            existing_weights_to_sum = g.ep['weight']
            summed_map = gt.contract_parallel_edges(g, existing_weights_to_sum)
        else:
            summed_map = gt.contract_parallel_edges(g)
        
        g.ep["weight"] = summed_map 
        processed_weight_map = summed_map

    return g, processed_weight_map


def directed_to_undirected_sum_weights(
    g_directed: gt.Graph, 
    existing_weight_name = None,
    inplace: bool = False
) -> tuple[gt.Graph, gt.EdgePropertyMap]:
    if not g_directed.is_directed():
        raise ValueError("Input graph must be directed.")

    if inplace:
        g_undirected = g_directed
        g_undirected.set_directed(False)
    else:
        g_undirected = gt.Graph(g_directed, directed=False)

    graph_result, result_map = simplify_graph_with_weights(g_undirected, weight_name=existing_weight_name, inplace=True)
    
    return graph_result, result_map

