import mesa
import mesa_geo as mg
import pyproj
from shapely.geometry import LineString, Point
from typing import List
from util import UnitTransformer,redistribute_vertices
    
# reference: https://github.com/projectmesa/mesa-examples/blob/main/gis/agents_and_networks
class Commuter(mg.GeoAgent):
    unique_id: int  # commuter_id, used to link commuters and nodes
    model: mesa.Model
    geometry: Point
    crs: pyproj.CRS
    origin: mesa.space.FloatCoordinate # where he begins his trip
    destination: mesa.space.FloatCoordinate  # the destination he wants to arrive at
    my_path: List[
        mesa.space.FloatCoordinate
    ]  # a set containing nodes to visit in the shortest path
    step_in_path: int  # the number of step taking in the walk
    status: str  # work, home, or transport
    SPEED: float

    def __init__(self, unique_id, model, geometry, crs) -> None:
        super().__init__(unique_id, model, geometry, crs)
        self.speed = 20.
    
    def _path_select(self) -> None:
        self.step_in_path = 0
        if (
            cached_path := self.model.network.get_cached_path(
                source=self.origin, target=self.destination
            )
        ) is not None:
            self.my_path = cached_path
        else:
            self.my_path = self.model.network.get_shortest_path(
                source=self.origin, target=self.destination
        )
            self.model.network.cache_path(
                source=self.origin,
                target=self.destination,
                path=self.my_path,
            )
        self._redistribute_path_vertices()

    def _redistribute_path_vertices(self) -> None:
        # if origin and destination share the same entrance, then self.my_path
        # will contain only this entrance node,
        # and len(self.path) == 1. There is no need to redistribute path vertices.
        if len(self.my_path) > 1:
            unit_transformer = UnitTransformer(degree_crs=self.model.network.crs)
            original_path = LineString([Point(p) for p in self.my_path])
            # from degree unit to meter
            path_in_meters = unit_transformer.degree2meter(original_path)
            redistributed_path_in_meters = redistribute_vertices(
                path_in_meters, self.speed
            )
            # meter back to degree
            redistributed_path_in_degree = unit_transformer.meter2degree(
                redistributed_path_in_meters
            )
            self.my_path = list(redistributed_path_in_degree.coords)
    
    def _prepare_to_move(self,origin,destination) -> None:
        self.origin = origin
        self.destination = destination
        self._path_select()
            
    
    def _move(self) -> None:
        if self.step_in_path < len(self.my_path):
            next_position = self.my_path[self.step_in_path]
            self.model.space.move_commuter(self, next_position)
            self.step_in_path += 1
        else:
            self.model.space.move_commuter(self, self.destination)
