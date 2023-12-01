import mesa_geo as mg
import numpy as np
import mesa
from agent import BDIAgent,Commuter
from shapely.geometry import Point,Polygon,LineString
import random
from collections import Counter
from util import UnitTransformer,redistribute_vertices

HEIGHT_PER_FLOOR = 3

class Floor(mg.GeoAgent):
    def __init__(self, unique_id, model, geometry, crs=None, render=True):
        if not crs:
            crs = model.crs
        super().__init__(unique_id, model, geometry, crs)
        self.render = render
        self.is_project = False
        self.new = False
    def step(self):
        pass

class Building(mesa.Agent):
    def __init__(self, unique_id, model, floors, bld, render=True):
        super().__init__(unique_id, model)
        self.floors = sorted(floors, key=lambda x: x.floor)
        self.bld = bld
        self.Category = self.floors[0].Category
        self.total_floor = len(self.floors)
        self.render = render
        self.order_list = {
            "daycare":0,
            "phamacy":1,
            "grocery":2,
            "office_lab":4,
            "family_housing":5,
            "workforce_housing":6,
            "early_career_housing":7,
            "executive_housing":8,
            "senior_housing":9,
        }
        for floor in self.floors:
            self.order_list[floor.Category] = 3
    
    def add_floor(self, floor):
        self.floors.append(floor)
        self.total_floor += 1
        self.reorganize()
    
    def reorganize(self):
        floors = sorted(self.floors, key=lambda x: self.order_list[x.Category])
        for i,floor in enumerate(floors):
            floor.floor = i
            floor.ind = str(self.bld)+"_"+str(floor.floor)
            _coords = [(x, y, HEIGHT_PER_FLOOR*i) for x, y, z in list(floor.geometry.exterior.coords)]
            floor.geometry = Polygon(shell=_coords)

    def step(self):
        pass


class Resident(Commuter, BDIAgent):
    def __init__(self, unique_id, model, geometry, crs=None, render=True):
        if not crs:
            crs = model.crs
        Commuter.__init__(self,unique_id, model, geometry, crs)
        BDIAgent.__init__(self,unique_id, model)

        self.house = None
        self.office = None
        self.render = render
        self.status = "office"
        self._elevator_step = 0
        #unit m/step
        self.speed = 1.2*model.minute_per_step*60
        self.target = None
        self.path_data = []

    def _random_point_in_polygon(self,polygon):
        minx, miny, maxx, maxy = polygon.bounds
        self.offset = min(maxx-minx,maxy-miny)*0.2
        z = polygon.exterior.coords[0][2]
        while True:
            pnt = Point(np.random.uniform(minx+ self.offset, maxx- self.offset), np.random.uniform(miny+ self.offset, maxy- self.offset),z)
            # pnt = Point(np.random.uniform(minx+offset, maxx-offset), np.random.uniform(miny+offset, maxy-offset))
            if polygon.contains(pnt):
                break
        return pnt

    def set_house(self, house):
        self.house = house
        self.house_point = self._random_point_in_polygon(self.house.geometry)
        self.geometry = self.house_point
        #there is a bug in triplayer of deck.gl, if only the z axis is changed, the path will not be rendered
        #so I shuffled the x,y a little bit
        #it takes 5 steps max to go up or down
        total_elevator_step_ = 5
        self.house_elevator = [(self.house_point.x+random.random()*self.offset*0.1,self.house_point.y+random.random()*self.offset*0.1,
                                max(self.house_point.z-i*HEIGHT_PER_FLOOR*total_elevator_step_,0))
                                for i in range(1,int(self.house.floor//total_elevator_step_))]

    def set_office(self, office):
        self.office = office
        self.office_point = self._random_point_in_polygon(self.office.geometry)
        #there is a bug in triplayer of deck.gl, if only the z axis is changed, the path will not be rendered
        #so I shuffled the x,y a little bit
        #it takes 5 steps max to go up or down
        total_elevator_step_ = 5
        self.office_elevator = [(self.office_point.x+random.random()*self.offset*0.1,self.office_point.y+random.random()*self.offset*0.1,
                                 max(self.office_point.z-i*HEIGHT_PER_FLOOR*total_elevator_step_,0))
                                 for i in range(1,int(self.office.floor//total_elevator_step_))]
    
    def prepare_to_move(self):
        #time_schedule
        if self.model.step_count == 8*60//self.model.minute_per_step:
            self.target = self.office_point
        # if self.model.step_count == 12*60//self.model.minute_per_step:
        #     self.target = self.house_point
        # if self.model.step_count == 13*60//self.model.minute_per_step:
        #     self.target = self.office_point
        # if self.model.step_count == 18*60//self.model.minute_per_step:
        #     self.target = self.house_point

        #path
        if self.target and self.status != "transport":
            #2d calculation path
            self.origin = (self.geometry.x,self.geometry.y)
            self.destination = (self.target.x,self.target.y)
            self._prepare_to_move(self.origin,self.destination)
            #there is a bug in triplayer of deck.gl, if only the z axis is changed, the path will not be rendered
            #so I shuffled the x,y a little bit
            #it takes 5 steps max to go up or down
            total_elevator_step_ = 5
            self.origin_elevator = [(self.geometry.x+random.random()*self.offset*0.1,self.geometry.y+random.random()*self.offset*0.1,
                                 max(self.geometry.z-i*HEIGHT_PER_FLOOR*total_elevator_step_,0))
                                 for i in range(1,int(self.office.floor//total_elevator_step_))]
            self.destination_elevator = [(self.target.x+random.random()*self.offset*0.1,self.target.y+random.random()*self.offset*0.1,
                                 max(self.target.z-i*HEIGHT_PER_FLOOR*total_elevator_step_,0))
                                 for i in range(1,int(self.office.floor//total_elevator_step_))]
            #simulation path
            self.my_path = [(x,y,0) for (x,y) in self.my_path]
            self.my_path = self.origin_elevator + self.my_path + list(reversed(self.destination_elevator)) + [list(self.target.coords)]
            self.status = "transport"
            #animation path
            self.path_data = {"path":self.my_path,"timestamps":[self.model.step_count+i for i in range(len(self.my_path))]}


        
    def move(self):
        if self.target:
            self._move()
            if self.geometry == self.office_point:
                self.status = "office"
                self.target = self.house_point
            if self.geometry == self.house_point:
                self.status = "house"
                self.target = self.office_point
            # if self.geometry == self.target:
            #     self.target = None


    def parallel_step(self):
        self.prepare_to_move()
        self.move()
        
    def step(self):
        pass