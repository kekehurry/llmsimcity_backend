
from agent.kendall_agents import *
from model.kendall_model import Kendall
from shapely.geometry import mapping
from util import CacheData
import os,sys
# dir_path = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(dir_path)

 
#Agent property
def get_agent_property(agent):
    properties = {}
    if isinstance(agent, Floor):
        properties["category"] = agent.Category
        properties["floor"] = agent.floor
        properties["ind"] = agent.ind
        properties["new"] = agent.new
        properties["is_project"] = agent.is_project
        properties["type"] = "floor"
    if isinstance(agent, Resident):
        properties["status"] = agent.status
        properties["type"] = "resident"
    return properties

#Get Geojson data
def get_render_data(model,properties_method=None):
    # resident_data = []
    path = []
    resident_data = {"type": "FeatureCollection", "features": []}
    abm_data = []
    for agent in model.space.agents:
        if agent.render:
            transformed_geometry = agent.get_transformed_geometry(
                model.space.transformer
            )
            properties = {}
            if properties_method:
                properties = properties_method(agent)
            geojson_geometry = mapping(transformed_geometry)
            if isinstance(agent, Resident):
                resident_data["features"].append({
                    "type": "Feature",
                    "geometry": geojson_geometry,
                    "properties": properties,
                    })
            if isinstance(agent, Resident):
                abm_data.append({
                    "coordinates":geojson_geometry["coordinates"],
                    "properties": properties,
                })
                path.append(agent.path_data)

    return {
            # 'building_data':building_data,
            'resident_data':resident_data,  
            'abm_data':abm_data,
            # 'collected_data':model.datacollector.data,
            'path':path,
            'step_count':model.step_count,
            # 'time' : '{:02d}:{:02d}'.format(model.hour,model.minute),
            }