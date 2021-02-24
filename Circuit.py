import json

class Circuit:
	'number of circuits
	NumCircuits = 0
	
	def __init__(self, name, port, percentage, flow_l_min):
		self.name = name
		self.port = port
		self.percentage = percentage
		self.flow_l_min = self
		Circuit.NumCircuits += 1
		
	def displayCircuit(self):
		return json.dumps(self.__dict__)