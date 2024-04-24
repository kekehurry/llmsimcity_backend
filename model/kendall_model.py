# import sys,os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mesa
import mesa_geo as mg
from agent.kendall_agents import *
from tqdm import tqdm
import numpy as np
import random
from schedule import ParallelActivation
from space import RoadNetwork,CommuteSpace
from model import DataCollector
from itertools import groupby
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed


class Kendall(mesa.Model):
    def __init__(self,
                 building_file:str,
                 road_file:str,
                 population:int,
                 crs:str ='epsg:4326'):
        super().__init__()

        self.building_file = building_file
        self.population = population
        self.buildings = []
        self.residents = []
        self.crs = crs

         #initialize time
        
        self.minute_per_step = 1
        self.hour = 8
        self.minute = 0
        self.step_count = self.hour*60//self.minute_per_step + self.minute//self.minute_per_step
        
        #init network
        self.network = RoadNetwork(road_file=road_file, crs=crs)

        #initialize model
        self.set_space_and_schedule()

        #initialize agents
        self.init_agents()

        #initialize datacollector
        self.datacollector = DataCollector(self)
        self.datacollector.collect_data()

    #initialize space and schedule
    def set_space_and_schedule(self):
        self.space = CommuteSpace(crs=self.crs,warn_crs_conversion=False)
        self.schedule = ParallelActivation(self)

    def create_agent(self, potential_house_, potential_office_):
        house = random.choices(potential_house_, weights=[x.area for x in potential_house_], k=10)[0]
        office = random.choices(potential_office_, weights=[x.area for x in potential_office_], k=10)[0]
        resident = Resident(self.next_id(), self, None, self.crs, render=True)
        resident.set_house(house)
        resident.set_office(office)
        resident.prepare_to_move()
        return resident
    
    def init_agents(self):
        #floors
        self.floors = self._load_from_file('floors', self.building_file, Floor)

        #buildings
        buildings_ = groupby(self.floors, lambda x: x.bld)
        for bld, floors in tqdm(buildings_, "create buildings"):
            building = Building(self.next_id(), self, list(floors), bld, render=False)
            building.reorganize()
            self.buildings.append(building)

        
        potential_house_ = [x for x in self.floors if x.Category in ["Residential","Mixed Use Residential"]]
        potential_office_ = [x for x in self.floors if x.Category not in ["Residential","Mixed Use Residential"]]
        #residents
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.create_agent, potential_house_, potential_office_) for _ in range(self.population)]
            for future in tqdm(as_completed(futures),total=len(futures),desc="create residents"):
                    self.residents.append(future.result())
                    self.schedule.add(future.result()) 
                    self.space.add_commuter(future.result())
        # for j in tqdm(range(self.population),"create residents"):
        #     self.create_agent(potential_house_, potential_office_)
            # house = random.choices(potential_house_, weights=[x.area for x in potential_house_], k=10)[0]
            # office = random.choices(potential_office_, weights=[x.area for x in potential_office_], k=10)[0]
            # house = random.choice(potential_house_)
            # office = random.choice(potential_office_)
            # resident = Resident(self.next_id(), self, None, self.crs, render=True)
            # resident.set_house(house)
            # resident.set_office(office)
            # resident.prepare_to_move()
            # self.residents.append(resident)
            # self.schedule.add(resident) 
            # self.space.add_commuter(resident)

    #load agents from gis files
    def _load_from_file(self, key:str, file:str, agent_class:mg.GeoAgent, id_key:str="index"):
        agentcreator = mg.AgentCreator(agent_class=agent_class, model=self)
        if file.endswith('.json'):
            agents = agentcreator.from_GeoJSON(open(file).read())
        else:
            agents = agentcreator.from_file(file, unique_id=id_key)
        self.space.add_agents(agents)
        self.__setattr__(key,agents)
        self.current_id = len(agents)
        return agents
    
    def _update_time(self):
        self.hour = self.step_count * self.minute_per_step // 60
        self.minute = self.step_count * self.minute_per_step % 60
    
    def step(self):
        self.schedule.step()
        self.datacollector.collect_data()
        self._update_time()
        self.step_count += 1


if __name__ == "__main__":
    model_params ={
    "building_file": 'data/kendall_buildings.json',
    "road_file": "data/kendall_roads.shp",
    "population": 10,
    }
    model = Kendall(**model_params)
    model.step()