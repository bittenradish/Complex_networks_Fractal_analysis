import graph_tool.all as gt
import numpy as np
import pandas as pd
import os
import json
import glob
import subprocess
import shlex
import multiprocessing
import logging
from typing import Callable

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
           'start_box_covering_pipeline',
           'in_separate_process',
           'config_logging',
           'calculate_assortativity',
           'create_series',
           'create_nan_series'
           ]

# Flow Variables

analysis_folder = "./analysis_data/"

# Flow functions

## General functions

def config_logging(into: str):
    logging.basicConfig(
        filename=into,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )

def in_separate_process(run: Callable, withArgs: tuple, log_as: str = ''):
    func_name = run.__name__
    process_identifier = f"{func_name} | Log ID: {log_as if log_as else str(withArgs)}"

    print(f"--- Processing: {process_identifier} ---")
    logging.info(f"START: {process_identifier}")

    # Create a separate process
    p = multiprocessing.Process(target=run, args=withArgs)
    
    p.start()
    p.join()

    # Check exit code
    if p.exitcode != 0:
        error_msg = f"FAILED: {process_identifier} - Process terminated with exit code: {p.exitcode}"
        print(f"!!! {error_msg}")
        logging.error(error_msg)
    else:
        success_msg = f"SUCCESS: {process_identifier}"
        print(success_msg)
        logging.info(success_msg)

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


## Metrics functions

def calculate_assortativity(graph, degree_property):
    assortativity_undirected, variance_undirected = gt.assortativity(graph, deg=degree_property)
    return assortativity_undirected, variance_undirected


def create_series(
        graph_name,
        is_mst,
        modularity_score,
        small_world_result,
        hcs_std,
        hcs_mean,
        assortativity_undirected,
        variance_undirected,
        fit_pl,
        fit_exp,
        wmse_pl,
        wmse_exp,
        pl_ex_ratio
):
    return pd.Series({
        'name': graph_name,
        'is_mst': is_mst,
        'modularity': modularity_score,
        'small_world': small_world_result.to_dict() if small_world_result is not np.nan else np.nan,
        'hcs_std': hcs_std,
        'hcs_mean': hcs_mean,
        'assortativity': assortativity_undirected,
        'variance': variance_undirected,
        'fit_pl': fit_pl,
        'fit_exp': fit_exp,
        'wmse_pl': wmse_pl,
        'wmse_exp': wmse_exp,
        'pl_ex_ratio': pl_ex_ratio
    })


def create_nan_series(graph_name, is_mst):
    return create_series(
        graph_name=graph_name,
        is_mst=is_mst,
        modularity_score=np.nan,
        small_world_result=np.nan,
        hcs_std=np.nan,
        hcs_mean=np.nan,
        assortativity_undirected=np.nan,
        variance_undirected=np.nan,
        fit_pl=np.nan,
        fit_exp=np.nan,
        wmse_pl=np.nan,
        wmse_exp=np.nan,
        pl_ex_ratio=np.nan
    )


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

