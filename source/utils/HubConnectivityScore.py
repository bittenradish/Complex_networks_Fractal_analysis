import graph_tool.all as gt
import numpy as np

def calculate_hcs_pair(graph, z_score_threshold=2.0, degree_type="total"):
    num_vertices = graph.num_vertices()
    if num_vertices == 0:
        return (0.0, 0.0)

    try:
        degrees_prop = graph.degree_property_map(degree_type)

        degrees_array = degrees_prop.a

        if degrees_array.size == 0:
             print("Warning: Graph has vertices but degree array is empty.")
             return (0.0, 0.0)

        mean_degree = np.mean(degrees_array)
        std_dev_degree = np.std(degrees_array)

        if std_dev_degree == 0:
             print(f"INFO: Standard deviation of degrees is 0. No hubs possible.")
             return (0.0, 0.0)

        # hub threshold bassed on standard deviation
        hub_threshold_std = mean_degree + z_score_threshold * std_dev_degree

        # hub threshold based on mean degree
        hub_threshold_mean = mean_degree * 2

        hcs_std = apply_hcs_threshold(hub_threshold_std, graph, degrees_array)
        hcs_mean = apply_hcs_threshold(hub_threshold_mean, graph, degrees_array)

        return (hcs_std, hcs_mean)

    except Exception as e:
        print(f"An error occurred during HCS calculation: {e}")
        return (0.0, 0.0)
    
def apply_hcs_threshold(threshold, graph, degrees_array):
        is_hub = graph.new_vertex_property("bool")
        
        # A node is a hub if its degree > threshold
        is_hub.a = (degrees_array > threshold)


        N_hub = is_hub.a.sum()

        if N_hub == 0:
            return 0.0

        hub_subgraph = gt.GraphView(graph, vfilt=is_hub)
        E_hub = hub_subgraph.num_edges()

        hcs = E_hub / N_hub if N_hub > 0 else 0.0

        print(f"Info: Found N_hub={N_hub} hubs (degree > {threshold:.2f}).")
        print(f"Info: Found E_hub={E_hub} edges among hubs.")

        return hcs