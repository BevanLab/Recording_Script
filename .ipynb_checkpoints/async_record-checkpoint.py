import PySpin
from camera import Camera
from multiprocessing import Process
import png
import argparse
import numpy as np

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

parser = argparse.ArgumentParser(description='Process Camera Inputs.')


parser.add_argument('--task', metavar = 'task', type = str, default = 'open-field')
parser.add_argument('--fps', metavar = 'fps', type = int, default = 220)
parser.add_argument('--time', metavar = 'time', type = float, default = 15)



args = parser.parse_args()




async def acquire_images(queue: asyncio.Queue, cam: PySpin.Camera):
    """
    A coroutine that captures `NUM_IMAGES` images from `cam` and puts them along
    with the camera serial number as a tuple into the `queue`.
    """
    # Set up camera
    cam_id = cam.GetUniqueID()
    cam.Init()
    cam.BeginAcquisition()
    prev_frame_ID = 0

    # Acquisition loop
    for i in range(NUM_IMAGES):
        img = cam.GetNextImage()
        frame_ID = img.GetFrameID()
        if img.IsIncomplete():
            print('WARNING: img incomplete', frame_ID,
                  'with status',
                  PySpin.Image_GetImageStatusDescription(img.GetImageStatus()))
            prev_frame_ID = frame_ID
            continue
        if frame_ID != prev_frame_ID + 1:
            print('WARNING: skipped frames', frame_ID)
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

    
    
async def save_images(queue: asyncio.Queue, save_dirs: dict, ext='.png'):
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
        frame_id = image.GetFrameID()
        filename = cam_id + '_' + str(frame_id) + ext
        filename = os.path.join(save_dirs[cam_id], filename)
        # Save the image using a pool of threads
        await loop.run_in_executor(tpe, save_image, image, filename)
        queue.task_done()
        print('[{}] Saved image {}'.format(cam_id, filename))


def save_image(image: PySpin.Image, filename: str):
    """
    Saves the given `image` under the given `filename`.
    """
    # Notice how CPU time is minimized and I/O time is maximized
    image.Save(filename)

    
    
    
    
async def main():
    # Set up cam_list and queue
    
    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()
    queue = asyncio.Queue()

    # Match serial numbers to save locations
    assert len(cam_list) <= len(SAVE_DIRS), 'More cameras than save directories'
    #camera_sns = [cam.GetUniqueID() for cam in cam_list]
    side = Camera('20400920', True, system, 'side', 'side.yaml')
    bottom = Camera('20400910', False, system, 'bottom', 'bottom.yaml')
    top = Camera('20400913', False, system, 'top', 'top.yaml')
    camera_sns = [side.serial]
    SAVE_DIRS = ['C:\\Videos\\side']
    save_dir_per_cam = dict(zip(camera_sns, SAVE_DIRS))
    NUM_IMAGES = args.fps * args.time  # The number of images to capture
    NUM_SAVERS = 20
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
    cam_list.Clear()
    system.ReleaseInstance()

# The event loop and Thread Pool Executor are global for convenience.
loop = asyncio.get_event_loop()
tpe = ThreadPoolExecutor(None)
loop.run_until_complete(main())
