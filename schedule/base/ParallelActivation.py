from mesa.time import BaseScheduler
# from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor

class ParallelActivation(BaseScheduler):

    def do_single(self,method, agent_key):
        getattr(self._agents[agent_key], method)()
        return "done"
    
    def parallel_do_each(self, method, agent_keys=None, shuffle=False):
        if agent_keys is None:
            agent_keys = self.get_agent_keys()
        if shuffle:
            self.model.random.shuffle(agent_keys)
        
        # with Pool() as pool:
        #     pool.starmap(self.do_single, [(method, agent_key) for agent_key in agent_keys])

        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.do_single, method, agent_key) for agent_key in agent_keys]
    
    def step(self):
        self.parallel_do_each('parallel_step')
        self.do_each('step')
        self.steps += 1
        self.time += 1
