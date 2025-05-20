import numpy as np
import graph_tool.all as gt
from random import sample

class SmallWorldDictKeys:
    CLUSTERING_COEFFICIENT = 'clustering_coefficient'
    EDGE_NUM = 'edge_num'
    VERTICE_NUM = 'vertice_num'
    L_AVG_ESTIMATED = 'l_avg_estimated'
    L_MEANS_STD = 'l_means_std'
    CLUSTERING_COEFFICIENT_RANDOM = 'clustering_coefficient_random'
    CLUSTERING_COEFFICIENT_NORMALIZED = 'clustering_coefficient_normalized'
    L_EXPECTED_RANDOM = 'l_expected_random'
    L_NORMALIZED = 'l_normalized'
    SMALL_WORLD_COEFFICIENT = 'small_world_coefficient'

    
class SmallWorldResult:
    def __init__(
        self,
        clustering_coefficient,
        edge_num,
        vertice_num,
        l_avg_estimated,
        l_means_std,
    ):
        self.clustering_coefficient = clustering_coefficient
        self.edge_num = edge_num
        self.vertice_num = vertice_num
        #Estimated avg shortest path length
        self.l_avg_estimated = l_avg_estimated
        self.l_means_std = l_means_std

    #Appoximate clusterin coefficient: number of edges / number of possible edges in undirected graph
    @property
    def clustering_coefficient_random(self):
        try:
            return self.edge_num / (self.vertice_num * (self.vertice_num - 1) / 2)
        except:
            return np.nan

    @property
    def clustering_coefficient_normalized(self):
        try:
            return self.clustering_coefficient / self.clustering_coefficient_random
        except:
            return np.nan

    # Expected avg shortest path length for random graph
    @property
    def l_expected_random(self):
        try:
            return (np.log(self.vertice_num) - 0.5772157) / np.log(2 * self.edge_num / self.vertice_num) + .5
        except:
            return np.nan

    @property
    def l_normalized(self):
        try:
            return self.l_avg_estimated / self.l_expected_random
        except:
            return np.nan

    @property
    def small_world_coefficient(self):
        try:
            return self.clustering_coefficient_normalized / self.l_normalized
        except:
            return np.nan
        
    def to_dict(self):
        return {
            SmallWorldDictKeys.CLUSTERING_COEFFICIENT : self.clustering_coefficient,
            SmallWorldDictKeys.EDGE_NUM : self.edge_num,
            SmallWorldDictKeys.VERTICE_NUM : self.vertice_num,
            SmallWorldDictKeys.L_AVG_ESTIMATED : self.l_avg_estimated,
            SmallWorldDictKeys.L_MEANS_STD : self.l_means_std,
            SmallWorldDictKeys.CLUSTERING_COEFFICIENT_RANDOM : self.clustering_coefficient_random,
            SmallWorldDictKeys.CLUSTERING_COEFFICIENT_NORMALIZED : self.clustering_coefficient_normalized,
            SmallWorldDictKeys.L_EXPECTED_RANDOM : self.l_expected_random,
            SmallWorldDictKeys.L_NORMALIZED : self.l_normalized,
            SmallWorldDictKeys.SMALL_WORLD_COEFFICIENT : self.small_world_coefficient
        }


    # Small world result builder function
    @staticmethod
    def build(g, n_threshold=50000, num_dist=1000, iterations=10):
        n = g.num_vertices()
        if n >= 3:
            edge_num = g.num_edges()

            c = gt.global_clustering(g)[0]

            # Calculate path length
            if n < n_threshold:
                # Calculate shortest distance[]
                distance_arr = gt.shortest_distance(g)
                # Avg shortest distance
                mean_l = np.mean([distance_arr[v].a.sum()/(n - 1) for v in g.vertices()])
                l_mean_std = np.nan
            else:
                l_mean_arr = []
                for i in range(iterations):
                    vertices = sample(list(g.vertices()), 2 * num_dist)

                    # Calculate shortest distance[]
                    distance_arr = [gt.shortest_distance(
                        g, source=vertices[j], target=vertices[j + int(num_dist / 2)]) for j in range(num_dist)]

                    # Avg shortest distance
                    l_mean_arr.append(np.mean(distance_arr))

                # estimated avg shortest path length
                mean_l = np.mean(l_mean_arr)

                # std of path length
                l_mean_std = np.std(l_mean_arr)

            return SmallWorldResult(
                    clustering_coefficient=c, 
                    edge_num=edge_num, 
                    vertice_num=n, 
                    l_avg_estimated=mean_l, 
                    l_means_std=l_mean_std
                )
        else:
            return SmallWorldResult(np.nan, np.nan, np.nan, np.nan, np.nan)
