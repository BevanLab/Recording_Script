# =============================================================================
# Copyright (c) 2001-2020 FLIR Systems, Inc. All Rights Reserved.
#
# This software is the confidential and proprietary information of FLIR
# Integrated Imaging Solutions, Inc. ("Confidential Information"). You
# shall not disclose such Confidential Information and shall use it only in
# accordance with the terms of the license agreement you entered into
# with FLIR Integrated Imaging Solutions, Inc. (FLIR).
#
# FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
# SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
# SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
# THIS SOFTWARE OR ITS DERIVATIVES.
# =============================================================================

# SaveImagesHighBandwidth.py shows how to save images from two full-bandwidth
# Oryx cameras.

"""
This script is used to save images at high bandwidth.
Note: commenting out print statements can reduce the CPU load resulting in
fewer dropped/incomplete frames.

Relevant documentation: Saving Images at High Bandwidth (10GigE)

Python specific additions to the concurrency discussion from the article above:

# Multithreading
Python uses a Global Interrupt Lock (GIL) that prevents multiple threads from running in parallel.
This makes multithreading tricky and reduces the benefits of this approach.
It's still possible to gain a speedup using multithreading as it could reduce the time spent
waiting on the GetNextImage() call on an empty buffer.
Additionally, I/O threads don't get blocked by the GIL.

# Multiprocessing
The main issue with this approach is passing data between processes.
Python uses pickle to serialize data for inter process communication.
The limitation of pickle is that objects cannot be pickled.
This is a problem because the GetNextImage function returns a PySpin image object,
which cannot be passed to a saving process from the acquisition process.
It's possible to call GetData or GetNDArray on the image object to get the data
as a numpy array and then pass it to a saving process;
but these function calls are relatively slow and compounded with
pickling, copying, and unpickling, make for an ineffective approach.

# Asyncio
On its own, asyncio is a solid concurrency approach for this problem.
It's very similar to the multithreading approach as everything runs only in one thread
but concurrently. In addition to this, it's possible to combine asyncio with multithreading
by using the ThreadPoolExecutor from the asyncio module. This approach enables a single thread
(with multiple coroutines) for acquiring images and multiple I/O threads for writing data
to storage. It's important to note that the function to be run in the ThreadPoolExecutor
must minimize CPU time as context switching to this thread will block the main thread due
to the GIL. We recommend only calling the Save() function in the ThreadPoolExecutor.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor

import PySpin

NUM_IMAGES = 1000  # The number of images to capture
NUM_SAVERS = 10  # The number of saver coroutines
# The directories to save to camera i will save images to SAVE_DIRS[i]
SAVE_DIRS = ['D:/Temp', 'F:/Temp']


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
    camera_sns = [cam.GetUniqueID() for cam in cam_list]
    save_dir_per_cam = dict(zip(camera_sns, SAVE_DIRS))

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
