class DataCollector:
    def __init__(self, model):
        self.model = model
        self.data = {}
        self.record = {}
    
    def register(self, attr, record=True):
        if attr not in self.data.keys():
            self.data[attr] = []
            self.record[attr] = record
        

    def collect_data(self):
        for attr in self.data.keys():
            if self.record[attr]:
                self.data[attr].append(getattr(self.model, attr))
            else:
                self.data[attr] = getattr(self.model, attr)
            