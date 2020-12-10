import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import argparse
from tqdm import tqdm

parser = argparse.ArgumentParser(description='Converts All Raw Images in Directory to Output Directory.')

#parser.add_argument('--input', metavar = 'input', type = str, default = 'D:\\top')
#parser.add_argument('--output', metavar = 'output', type = str, default = 'D:\\top')

file_input = 'R:\\Core_Facilities\\PI\\Bevan_Lab_mbe377\\Open Field\\Multi-Cam Open Field\\Open filed - Male\\8458 - HET - NULL - 9 mth - Male\\'
file_output = 'R:\\Core_Facilities\\PI\\Bevan_Lab_mbe377\\Open Field\\Multi-Cam Open Field\\Open filed - Male\\8458 - HET - NULL - 9 mth - Male - converted\\'

#args = parser.parse_args()
try:
	os.makedirs(file_output)
	print('Output Directory Created')
except OSError as e:
	print('Output Directory Already Exists')

for img in tqdm(os.listdir(file_input)):
	name = img
	folder = name.split('-')[0]
	img = file_input + img
	img = np.fromfile(img, dtype = np.uint8).reshape(1080, 1440)
	#plt.imshow(img)
	#plt.show()
	
	try:
		os.makedirs(file_output + folder)
		print('Output Subdirectory Created')
	except OSError as e:	
		continue
	cv2.imwrite(file_output + folder + '\\' + name[:-4] +'.png', img)