import graph_tool.all as gt
import numpy as np

__all__ = ['is_weight_type_supported', 'has_parallel_edges', 'simplify_graph_with_weights']

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
