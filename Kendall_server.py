
from agent.kendall_agents import *
from model.kendall_model import Kendall
from shapely.geometry import mapping
from flask import Flask,jsonify,request
from flask_cors import CORS
import os,sys
from util import CacheData

dir_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(dir_path)

app = Flask(__name__)
CORS(app)
 
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
    resident_data = []
    path = []
    building_data = {"type": "FeatureCollection", "features": []}
    for agent in model.space.agents:
        if agent.render:
            transformed_geometry = agent.get_transformed_geometry(
                model.space.transformer
            )
            properties = {}
            if properties_method:
                properties = properties_method(agent)
            geojson_geometry = mapping(transformed_geometry)
            if isinstance(agent, Floor):
                building_data["features"].append({
                    "type": "Feature",
                    "geometry": geojson_geometry,
                    "properties": properties,
                    })
            if isinstance(agent, Resident):
                resident_data.append({
                    "coordinates":geojson_geometry["coordinates"],
                    "properties": properties,
                })
                path.append(agent.path_data)

    return {'building_data':building_data,
                    'resident_data':resident_data,  
                    'collected_data':model.datacollector.data,
                    'path':path,
                    'step_count':model.step_count,
                    'time' : '{:02d}:{:02d}'.format(model.hour,model.minute),
                    }

#Init Model
model_params ={
    "building_file": os.path.join(dir_path,'data/kendall_buildings.json'),
    "road_file": os.path.join(dir_path,"data/kendall_roads.shp"),
    "population": 1000,
    "crs" : "epsg:4326",
    }

model = Kendall(**model_params)
print("Model loaded")
init_step = model.step_count
init_render = get_render_data(model,properties_method=get_agent_property)
cacha_database = CacheData(capacity=60*24)
cacha_database.clear_cache_data()
cacha_database.add_cache_data(init_step,init_render)

#APIs
@app.route('/init')
def run():
    _init_step,_init_data = cacha_database.get_oldest_data()
    model.step_count = _init_step
    return _init_data

@app.route('/cache')
def cache():
    model.step()
    render_data = get_render_data(model,properties_method=get_agent_property)
    if not cacha_database.key_exists(model.step_count):
        cacha_database.add_cache_data(model.step_count,render_data)
    return jsonify(render_data)


@app.route('/step',methods=['POST']) 
def step():
    data = request.get_json()
    step_count = data['step_count']
    if cacha_database.key_exists(step_count):
        model.step_count = step_count
        return cacha_database.get_cache_data(step_count)
    else:
        return cache()

@app.route('/reset',methods=['POST','GET'])
def reset(model_params=model_params):
    global model
    model_params_ = model_params
    if request.method == 'POST':
        model_params_ = request.get_json()
    model = Kendall(**model_params_)
    cacha_database.clear_cache_data()
    cacha_database.add_cache_data(init_step,init_render)
    return jsonify(init_render)

if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True, port=5001, use_reloader=False)

    # import time
    # for i in range(100):
    #     start = time.time()
    #     model.step()
    #     stop = time.time()
    #     print(stop-start)