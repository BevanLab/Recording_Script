
from multiprocessing import Queue
from utils import *
import os
import numpy as np
import png


class Camera:
	def __init__(self, serial: str, primary: bool, system, cam_name: str,\
		yaml_path: str):

		"""
		Initializes Camera
		"""
		self.stream_buffer = Queue()
		self.serial = serial
		self.primary = primary
		cam_list = system.GetCameras()
		self.cam = cam_list.GetBySerial(serial)
		self.cam_name = cam_name
		setup_cam(self.cam, yaml_path)
		print(cam_name + ' initialized!')
		if primary:
			self.cam.LineSelector.SetValue(PySpin.LineSelector_Line2)
			self.cam.V3_3Enable.SetValue(True)
		else:
			self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
			self.cam.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
			self.cam.TriggerOverlap.SetValue(PySpin.TriggerOverlap_ReadOut)
			self.cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
		
		self.img_num = 0
		print(cam_name + ' Trigger mode set!')
		
	def start_aquisition(self):
		nodemap = self.cam.GetNodeMap()
		node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
		if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
			print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
			return False

		# Retrieve entry node from enumeration node
		node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
		if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
			print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
			return False

		# Retrieve integer value from entry node
		acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

		# Set integer value from entry node as new value of enumeration node
		node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

		print('Acquisition mode set to continuous...')
		self.cam.BeginAcquisition()
		print('Aquisition has begun for ' + self.cam_name)

			#image_converted.Save(filename)
			#png.from_array(image_converted).save(filename)
			