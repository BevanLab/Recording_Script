import PySpin


import argparse

parser = argparse.ArgumentParser(description='Process Camera Inputs.')


parser.add_argument('--task', metavar = 'task', type = str, default = 'open-field')
parser.add_argument('--fps', metavar = 'fps', type = int, default = 225)
parser.add_argument('--fps', metavar = 'fps', type = int, default = 225)
parser.add_argument('--time', metavar = 'time', type = float, default = 15)


args = parser.parse_args()
print(args.accumulate(args.integers))
