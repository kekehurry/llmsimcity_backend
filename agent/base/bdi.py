from  mesa import Agent
import random

# define belief
class Belief:
    def __init__(self, key:str, value:object):
        self.key = key
        self.value = value

# define desire
class Desire:
    def __init__(self, key:str, intensity:float, lifetime:int):
        self.key = key
        self.intensity = intensity
        self.lifetime = lifetime

# define intention
class Intension:
    def __init__(self, key:str, action:callable):
        self.key = key
        self.action = action
    def act(self):
        return self.action()

# define relation
class Relation:
    def __init__(self, type:str, agent:Agent, intensity:float):
        self.type = type
        self.agent = agent
        self.intensity = intensity

# define BDI agent
class BDIAgent(Agent):
    
    def __init__(self, unique_id:int, model:object):
        super().__init__(unique_id, model)
        self.belief_base = {}
        self.desire_base = {}
        self.intension_base = {}
        self.relation_base = {}
        self.init_behaviors()
    
    def set_belief(self, key:str, value:object):
        #add or set belief
        self.belief_base[key] = Belief(key, value)
    
    def remove_belief(self, key:str):
        # remove belief if it exists
        if key in self.belief_base.keys():
            del self.belief_base[key]
    
    def set_desire(self, key:str, intensity:float, lifetime:int):
        #add or set desire
        self.desire_base[key] = Desire(key, intensity, lifetime)
    
    def get_desire(self, key:str):
        if key in self.desire_base.keys():
            return self.desire_base[key]
    
    def remove_desire(self, key:str):
        # remove desire if it exists
        if key in self.desire_base.keys():
            del self.desire_base[key]

    def update_desire(self):
        # update desire intensity by lifetime
        for key in self.desire_base.keys():
            # if lifetime is miner than 0, the desire is permanent
            if self.desire_base[key].lifetime > 0:
                self.desire_base[key].intensity -= 1/self.desire_base[key].lifetime
            if self.desire_base[key].intensity == 0:
                self.remove_desire(key)

    def get_current_desire(self,by_change=False):
        if len(self.desire_base) > 0:
            if by_change:
                #the chance of choosing a desire is proportional to its intensity
                desires = [self.desire_base[key] for key in self.desire_base]
                current_desire = random.choices(desires, weights=lambda x: x.intensity, k=1)[0]
            else:
                #the desire with the highest intensity is chosen
                desires = [self.desire_base[key] for key in self.desire_base]
                current_desire = max(desires, key=lambda x: x.intensity)
            return current_desire
        
    def set_intension(self,key,action):
        #add or set intension
        self.intension_base[key] = Intension(key, action)
    
    def get_current_intension(self,by_change=False):
        current_desire = self.get_current_desire(by_change=by_change)
        if current_desire is not None and current_desire.key in self.intension_base.keys():
            return self.intension_base[current_desire.key]
    
    def set_relation(self, type:str, agent:Agent, intensity:float):
        #add or set relation
        self.relation_base[agent.unique_id] = Relation(type, agent, intensity)
    
    def remove_relation(self, agent:Agent):
        # remove relation if it exists
        if agent.unique_id in self.relation_base.keys():
            del self.relation_base[agent.unique_id]
    
    def share_information(self,key:str, value:object, type:str, threshold:float):
        for relation in self.relation_base.values():
            if relation.intensity > threshold and relation.type == type:
                relation.agent.set_belief(key,value)

    def init_behaviors(self):
        pass
    
    def observe(self):
        # the rules of generating belief
        pass
    
    def think(self):
        # the rules of generating desire
        pass
    
    def act(self):
        #get desire, intesion and run
        return self.get_current_intension().run()