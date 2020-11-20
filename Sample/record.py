from pyspin import PySpin


import argparse

parser = argparse.ArgumentParser(description='Process Camera Inputs.')


parser.add_argument('--task', metavar = 'task', type = str, default = 'open-field')
parser.add_argument('--fps', metavar = 'fps', type = int, default = 225)
#parser.add_argument('--fps', metavar = 'fps', type = int, default = 225)
parser.add_argument('--time', metavar = 'time', type = float, default = 15)


args = parser.parse_args()
#print(args.accumulate(args.integers))


if args.task == 'open-field':
	overhead_serial = '20400913'
	side_serial = '20400920'
	under_serial = '20400910'
	system = PySpin.System.GetInstance()
	print('System Started')
	# Get camera list
	cam_list = system.GetCameras()
	print('Camera initialized')
	# Get cameras by serial
	overhead_camera = cam_list.GetBySerial(overhead_serial)
	side_camera = cam_list.GetBySerial(side_serial)
	under_camera = cam_list.GetBySerial(under_serial)
	print('all cameras started')

	overhead_camera.Init()
	side_camera.Init()
	under_camera.Init()
	print('all cameras init')

	# Set up primary camera trigger
	side_camera.LineSelector.SetValue(PySpin.LineSelector_Line2)
	side_camera.V3_3Enable.SetValue(True)
	 
	# Set up secondary camera trigger
	overhead_camera.TriggerMode.SetValue(PySpin.TriggerMode_Off)
	overhead_camera.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
	overhead_camera.TriggerOverlap.SetValue(PySpin.TriggerOverlap_ReadOut)
	overhead_camera.TriggerMode.SetValue(PySpin.TriggerMode_On)
	 
	# Set up secondary camera trigger
	under_camera.TriggerMode.SetValue(PySpin.TriggerMode_Off)
	under_camera.TriggerSource.SetValue(PySpin.TriggerSource_Line3)
	under_camera.TriggerOverlap.SetValue(PySpin.TriggerOverlap_ReadOut)
	under_camera.TriggerMode.SetValue(PySpin.TriggerMode_On)
	print('HW trigger defined')


	# Set acquisition mode to acquire a single frame, this ensures acquired images are sync'd since camera 2 and 3 are setup to be triggered
	side_camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame)
	overhead_camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame)
	under_camera.AcquisitionMode.SetValue(PySpin.AcquisitionMode_SingleFrame)
	 
	# Start acquisition; note that secondary cameras have to be started first so acquisition of primary camera triggers secondary cameras.
	side_camera.BeginAcquisition()
	under_camera.BeginAcquisition()
	overhead_camera.BeginAcquisition()
	print('acquision started')
	# Acquire images
	image_1 = side_camera.GetNextImage()
	image_2 = overhead_camera.GetNextImage()
	image_3 = under_camera.GetNextImage()
	print('images acquired')
	# Save images
	image_1.Save('cam_1.png')
	image_2.Save('cam_2.png')
	image_3.Save('cam_3.png')
	print('images saved')
	# Release images
	image_1.Release()
	image_2.Release()
	image_3.Release()
	print('images released')
	# end acquisition
	side_camera.EndAcquisition()
	under_camera.EndAcquisition()
	overhead_camera.EndAcquisition()
	print('ended acquisition')