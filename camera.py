
from multiprocessing import Queue


class Camera:
	def __init__(self, serial: str, primary: bool):

		"""
		Initializes Camera
		"""
		self.stream_buffer = Queue()
		self.serial = serial
		self.primary = primary
		
	def 