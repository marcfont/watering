import json

class Circuit:
	def __init__(self, name, port, percentage, flow_l_min):
		self.name = name
		self.port = port
		self.percentage = percentage
		self.flow_l_min = flow_l_min
		
	def displayCircuit(self):
		return json.dumps(self.__dict__, default=json_util.default)