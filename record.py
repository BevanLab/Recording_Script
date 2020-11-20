from pyspin import PySpin
from camera import Camera
from multiprocessing import Process
import png
import argparse
import numpy as np

parser = argparse.ArgumentParser(description='Process Camera Inputs.')


parser.add_argument('--task', metavar = 'task', type = str, default = 'open-field')
parser.add_argument('--fps', metavar = 'fps', type = int, default = 220)
parser.add_argument('--time', metavar = 'time', type = float, default = 15)


args = parser.parse_args()



system = PySpin.System.GetInstance()


side = Camera('20400920', True, system, 'side', 'side.yaml')
bottom = Camera('20400910', False, system, 'bottom', 'bottom.yaml')
top = Camera('20400913', False, system, 'top', 'top.yaml')

def record(n = 10000):
		while n:
			side.stream_buffer.put(np.asarray(side.cam.GetNextImage))
			#side.stream_buffer.put(n)
			n -= 1
		side.stream_buffer.put('end')

def save():
	while True:
		if side.stream_buffer.get() == 'end':
			break
		img = side.stream_buffer.get()
		#image_converted = img.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
		try:  
		    os.mkdir(cam_name)
		    filename = os.path.join(cam_name, acquisition_ + str(self.img_num).jpg)  
		except OSError as error:  
		    filename = os.path.join(cam_name, acquisition_ + str(self.img_num).jpg)  
		png.from_array(image_converted).save(filename)


bottom.start_aquisition()
top.start_aquisition()
side.start_aquisition()

side_save = Process(target=save)
side_save.daemon = True
#side_intake = Process(target=side.record)
record()
side_save.start() 