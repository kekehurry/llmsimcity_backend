from collections import defaultdict
from typing import DefaultDict, Dict, Set, List, Optional,Tuple, Union
import networkx as nx
import pyproj
from sklearn.neighbors import KDTree
import mesa
import mesa_geo as mg
from shapely.geometry import Point
import momepy
import geopandas as gpd
from agent import Commuter
import pickle
import os
from util import segmented

import warnings
warnings.filterwarnings("ignore")

FloatCoordinate = Tuple[float, float, Optional[float]]

class RoadNetwork:
    _nx_graph: nx.Graph
    _kd_tree: KDTree
    _crs: pyproj.CRS

    def __init__(self, road_file:str, crs: str):
        self.crs = crs
        road_df = gpd.read_file(road_file)
        lines=road_df["geometry"]
        segmented_lines = gpd.GeoDataFrame(geometry=segmented(lines))
        if self.crs:
            if segmented_lines.crs:
                segmented_lines.to_crs(self.crs, inplace=True)
            else:
                segmented_lines.set_crs(self.crs, inplace=True)
        G = momepy.gdf_to_nx(segmented_lines, approach="primal", length="length")
        self.nx_graph = G.subgraph(max(nx.connected_components(G), key=len))
        self._path_select_cache = {}
        # cache_foler = "cache"
        # if not os.path.exists(cache_foler):
        #     os.makedirs(cache_foler)
        # self._path_cache_result = os.path.join(cache_foler, "path_cache.pkl")
        # try:
        #     with open(self._path_cache_result, "rb") as cached_result:
        #         self._path_select_cache = pickle.load(cached_result)
        # except FileNotFoundError:
        #     self._path_select_cache = {}

    @property
    def nx_graph(self) -> nx.Graph:
        return self._nx_graph

    @nx_graph.setter
    def nx_graph(self, nx_graph) -> None:
        self._nx_graph = nx_graph
        self._kd_tree = KDTree(nx_graph.nodes)

    @property
    def crs(self) -> pyproj.CRS:
        return self._crs

    @crs.setter
    def crs(self, crs) -> None:
        self._crs = crs

    def get_nearest_node(
        self, float_pos: FloatCoordinate
    ) -> FloatCoordinate:
        node_index = self._kd_tree.query([float_pos], k=1, return_distance=False)
        node_pos = self._kd_tree.get_arrays()[0][node_index[0, 0]]
        return tuple(node_pos)

    def get_shortest_path(
        self, source: FloatCoordinate, target: FloatCoordinate
    ) -> List[FloatCoordinate]:
        from_node_pos = self.get_nearest_node(source)
        to_node_pos = self.get_nearest_node(target)
        # return nx.shortest_path(self.nx_graph, from_node_pos,
        #                         to_node_pos, method="dijkstra", weight="length")
        return nx.astar_path(self.nx_graph, from_node_pos, to_node_pos, weight="length")

    def cache_path(
        self,
        source: FloatCoordinate,
        target: FloatCoordinate,
        path: List[FloatCoordinate],
    ) -> None:
        # print(f"caching path... current number of cached paths:
        # {len(self._path_select_cache)}")
        self._path_select_cache[(source, target)] = path
        self._path_select_cache[(target, source)] = list(reversed(path))
        # with open(self._path_cache_result, "wb") as cached_result:
        #     pickle.dump((self._path_select_cache), cached_result)

    def get_cached_path(
        self, source: FloatCoordinate, target: FloatCoordinate
    ) -> List[FloatCoordinate]:
        return self._path_select_cache.get((source, target), None)


class CommuteSpace(mg.GeoSpace):
    _commuters_pos_map: DefaultDict[FloatCoordinate, Set[Commuter]]
    _commuter_id_map: Dict[int, Commuter]

    def __init__(self, crs: str, warn_crs_conversion:bool=False) -> None:
        super().__init__(crs=crs,warn_crs_conversion=warn_crs_conversion)
        self._commuters_pos_map = defaultdict(set)
        self._commuter_id_map = {}

    def get_commuters_by_pos(
        self, float_pos: FloatCoordinate
    ) -> Set[Commuter]:
        return self._commuters_pos_map[float_pos]

    def get_commuter_by_id(self, commuter_id: int) -> Commuter:
        return self._commuter_id_map[commuter_id]

    def add_commuter(self, agent: Commuter) -> None:
        super().add_agents([agent])
        self._commuters_pos_map[(agent.geometry.x, agent.geometry.y)].add(agent)
        self._commuter_id_map[agent.unique_id] = agent

    def move_commuter(
        self, commuter: Commuter, pos: FloatCoordinate
    ) -> None:
        # self.__remove_commuter(commuter)
        commuter.geometry = Point(pos)
        # self.add_commuter(commuter)

    def __remove_commuter(self, commuter: Commuter) -> None:
        super().remove_agent(commuter)
        del self._commuter_id_map[commuter.unique_id]
        self._commuters_pos_map[(commuter.geometry.x, commuter.geometry.y)].remove(
            commuter
        )