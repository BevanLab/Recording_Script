import yaml
from pyspin import PySpin
import os

def setup_cam(cam, yaml_path):
	""" This will setup (initialize + configure) input
	 camera given a path to a yaml file 
	 - Credit to https://github.com/justinblaber/multi_pyspin/blob/master/multi_pyspin.py"""

	if not os.path.isfile(yaml_path):
		raise RuntimeError('"' + yaml_path + '" could not be found!')

	# Print setup
	print(cam.GetUniqueID() + ' - setting up...')

	# Init camera
	cam.Init()

	# Load yaml file and grab init commands
	node_cmd_dicts = None
	with open(yaml_path, 'rb') as file:
		yaml_dict = yaml.load(file, Loader=yaml.SafeLoader)
		# Get commands from "init"
		if isinstance(yaml_dict, dict) and 'init' in yaml_dict:
			node_cmd_dicts = yaml_dict['init']

	# Perform node commands if they are provided
	if isinstance(node_cmd_dicts, list):
		# Iterate over commands
		for node_cmd_dict in node_cmd_dicts:
			if isinstance(node_cmd_dict, dict):
				# Get camera node string
				cam_node_str = list(node_cmd_dict.keys())
				if len(cam_node_str) == 1:
					cam_node_str = cam_node_str[0]

					# NOTE: I believe there should only be SetValue()'s and Execute()'s with RW access mode for
					# initialization of camera (read only doesn't make sense and the write onlys that I've seen are
					# mainly for rebooting the camera, which isn't necessary). If this is not the case, then the method
					# and/or access mode(s) will need to be added to the yaml file.

					# Get node argument (if it exists)
					cam_node_arg = None
					cam_node_dict = node_cmd_dict[cam_node_str]
					if isinstance(cam_node_dict, dict) and 'value' in cam_node_dict:
						cam_node_arg = cam_node_dict['value']

					# Get method
					if cam_node_arg is not None:
						# Assume this is a SetValue()
						cam_method_str = 'SetValue'
					else:
						# Assume this is an Execute()
						cam_method_str = 'Execute'

					# Get mode - Assume this is RW
					pyspin_mode_str = 'RW'

					# Perform command
					_node_cmd(cam,
							  cam_node_str,
							  cam_method_str,
							  pyspin_mode_str,
							  cam_node_arg)
				else:
					raise RuntimeError('Only one camera node per yaml "tick" is supported. '
									   'Please fix: ' + str(cam_node_str))



def _node_cmd(cam, cam_node_str, cam_method_str, pyspin_mode_str=None, cam_node_arg=None):
	""" Performs method on input cam node with optional access mode check """

	# Print command info
	info_str = cam.GetUniqueID() + ' - executing: "' + '.'.join([cam_node_str, cam_method_str]) + '('
	if cam_node_arg is not None:
		info_str += str(cam_node_arg)
	print(info_str + ')"')

	# Get camera node
	cam_node = cam
	cam_node_str_split = cam_node_str.split('.')
	for sub_cam_node_str in cam_node_str_split:
		cam_node = getattr(cam_node, sub_cam_node_str)

	# Perform optional access mode check
	#if pyspin_mode_str is not None:
		#if cam_node.GetAccessMode() != getattr(PySpin, pyspin_mode_str):
		#	raise RuntimeError('Access mode check failed for: "' + cam_node_str + '" with mode: "' +
		#					   pyspin_mode_str + '".')

	# Format command argument in case it's a string containing a PySpin attribute
	if isinstance(cam_node_arg, str):
		cam_node_arg_split = cam_node_arg.split('.')
		if cam_node_arg_split[0] == 'PySpin':
			if len(cam_node_arg_split) == 2:
				cam_node_arg = getattr(PySpin, cam_node_arg_split[1])
			else:
				raise RuntimeError('Arguments containing nested PySpin attributes are currently not supported...')

	# Perform command
	if cam_node_arg is None:
		return getattr(cam_node, cam_method_str)()
	else:
		return getattr(cam_node, cam_method_str)(cam_node_arg)