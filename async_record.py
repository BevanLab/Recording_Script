import PySpin
from camera import Camera
from multiprocessing import Process
import png
import argparse
import numpy as np

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
import cv2

parser = argparse.ArgumentParser(description='Process Camera Inputs.')


parser.add_argument('--task', metavar = 'task', type = str, default = 'open-field')
parser.add_argument('--fps', metavar = 'fps', type = int, default = 200)
parser.add_argument('--time', metavar = 'time', type = float, default = 60*5)
parser.add_argument('--numsavers', metavar = 'num-savers', type = int, default = 1)



args = parser.parse_args()
SAVE_DIRS = ['D:\\top', 'D:\\bottom', 'D:\\side']
NUM_SAVERS = args.numsavers
NUM_IMAGES = int(args.fps * args.time)  # The number of images to capture
NUM_BUFFERS = 3000
print(NUM_IMAGES)
print(NUM_SAVERS)
async def acquire_images(queue: asyncio.Queue, cam: PySpin.Camera):
    """
    A coroutine that captures `NUM_IMAGES` images from `cam` and puts them along
    with the camera serial number as a tuple into the `queue`.
    """
    # Set up camera

    cam_id = cam.serial
    print(cam_id)
    cam.start_aquisition()
    cam = cam.cam
    #cam.Init()

    print('aquisition started')

    prev_frame_ID = 0

    # Acquisition loop
    for i in range(NUM_IMAGES):
        try:
            img = cam.GetNextImage()
        except Exception as e:
            print(e)

        frame_ID = img.GetFrameID()
        if img.IsIncomplete():
            print('WARNING: img incomplete', frame_ID,
                  'with status',
                  PySpin.Image_GetImageStatusDescription(img.GetImageStatus()))
            prev_frame_ID = frame_ID
            continue
        if frame_ID != prev_frame_ID + 1:
            print('WARNING: skipped frame', frame_ID)
        prev_frame_ID = frame_ID
        queue.put_nowait((img, cam_id))

        print('Queue size:', queue.qsize())
        print('[{}] Acquired image {}'.format(cam_id, frame_ID))
        await asyncio.sleep(0)  # This is necessary for context switches

    # Clean up
    await queue.join()  # Wait for all images to be saved before EndAcquisition
    cam.EndAcquisition()
    cam.DeInit()
    del cam

    
    
async def save_images(queue: asyncio.Queue, save_dirs: dict, ext='.Raw'):
    """
    A coroutine that gets images from the `queue` and saves
    them using the global Thread Pool Executor.
    The save paths per camera are determined by `save_dirs` and the file
    extension is determined by the `ext` paramenter.
    `save_dirs` is a dict where the keys are the camera serial numbers
    and the values are the directory to save to.
    Once the image is saved, it is implicitly released and the task
    is marked as done in the queue.
    """
    while True:
        # Receive image
        image, cam_id = await queue.get()
        # Create filename
        #print('image received for saving')
        frame_id = image.GetFrameID()
        filename = str(frame_id) + ext
        
        print(save_dirs[cam_id])
        filename = os.path.join(save_dirs[cam_id], filename)
        print(filename)
        # Save the image using a pool of threads
        #print('saving file ' + filename )
        await loop.run_in_executor(tpe, save_image, image, filename)
        queue.task_done()
        print('[{}] Saved image {}'.format(cam_id, filename))


def save_image(image: PySpin.Image, filename: str):
    """
    Saves the given `image` under the given `filename`.
    """
    # Notice how CPU time is minimized and I/O time is maximized
    #print(filename + ' is being saved')
    #np_img = image.GetNDArray()
    image.Save(filename)
    #cv2.imwrite(filename, np_img)
    #print(filename + ' saved')

    
    
    
    
async def main():
    # Set up cam_list and queue
    
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    queue = asyncio.Queue()

    # Match serial numbers to save locations
    #assert len(cam_list) <= len(SAVE_DIRS), 'More cameras than save directories'
    #camera_sns = [cam.GetUniqueID() for cam in cam_list]
    
    bottom = Camera('20400910', False, system, 'bottom', 'bottom.yaml')
    top = Camera('20400913', False, system, 'top', 'top.yaml')
    side = Camera('20400920', True, system, 'side', 'side.yaml')
    
    for camera in [top, bottom, side]:
        cam = camera.cam
        s_node_map = cam.GetTLStreamNodeMap()

        # Set stream buffer Count Mode to manual
        stream_buffer_count_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferCountMode'))
        if not PySpin.IsAvailable(stream_buffer_count_mode) or not PySpin.IsWritable(stream_buffer_count_mode):
            print('Unable to set Buffer Count Mode (node retrieval). Aborting...\n')
            return False

        stream_buffer_count_mode_manual = PySpin.CEnumEntryPtr(stream_buffer_count_mode.GetEntryByName('Manual'))
        if not PySpin.IsAvailable(stream_buffer_count_mode_manual) or not PySpin.IsReadable(stream_buffer_count_mode_manual):
            print('Unable to set Buffer Count Mode entry (Entry retrieval). Aborting...\n')
            return False

        stream_buffer_count_mode.SetIntValue(stream_buffer_count_mode_manual.GetValue())
        print('Stream Buffer Count Mode set to manual...')

        # Retrieve and modify Stream Buffer Count
        buffer_count = PySpin.CIntegerPtr(s_node_map.GetNode('StreamBufferCountManual'))
        if not PySpin.IsAvailable(buffer_count) or not PySpin.IsWritable(buffer_count):
            print('Unable to set Buffer Count (Integer node retrieval). Aborting...\n')
            return False

        # Display Buffer Info
        print('Default Buffer Count: %d' % buffer_count.GetValue())
        print('Maximum Buffer Count: %d' % buffer_count.GetMax())

        buffer_count.SetValue(NUM_BUFFERS)

        print('Buffer count now set to: %d' % buffer_count.GetValue())
        


    camera_sns = [top.serial, bottom.serial,side.serial ]
    
    save_dir_per_cam = dict(zip(camera_sns, SAVE_DIRS))
    
    cam_list = [top, bottom, side]
    # Start the acquisition and save coroutines
    acquisition = [asyncio.gather(acquire_images(queue, cam)) for cam in cam_list]
    savers = [asyncio.gather(save_images(queue, save_dir_per_cam)) for _ in range(NUM_SAVERS)]

    # Wait for all images to be captured and saved
    await asyncio.gather(*acquisition)
    print('Acquisition complete.')

    # Cancel the now idle savers
    for c in savers:
        c.cancel()

    # Clean up
    cam_list = system.GetCameras()
    cam_list.Clear()
    system.ReleaseInstance()

# The event loop and Thread Pool Executor are global for convenience.
loop = asyncio.get_event_loop()
tpe = ThreadPoolExecutor(None)
loop.run_until_complete(main())
