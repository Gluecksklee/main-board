import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image
from tqdm import tqdm

from other.analyze_image import read_img
from utils.analysis import image_mean_brightness, as_quadratic_shape_as_possible


def create_timelapse(
        src_folder,
        dst_file,
        fps=24,
        size: Optional[tuple[int, int]] = (1920, 1440),
        take_every: int = 1,
        with_timestamp: bool = False,
        check_brightness: bool = True,
):
    src_folder = Path(src_folder)
    dst_file = Path(dst_file)

    img_files = sorted([
        file
        for file in src_folder.iterdir()
        if file.name.lower().endswith(".jpeg") or file.name.lower().endswith(".jpg")
    ])

    if size is None:
        img = cv2.imread(str(img_files[0]))
        size = img.shape

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    dst_file.parent.mkdir(exist_ok=True, parents=True)
    video = cv2.VideoWriter(str(dst_file), fourcc, fps, size)

    for i, img_file in enumerate(tqdm(img_files)):
        if i % take_every != 0:
            continue

        img = read_img(img_file)
        if check_brightness:
            mean_brightness = image_mean_brightness(img)
            if not (0.2 < mean_brightness < 0.8):
                continue
        # if i < 922:
        #     img = img[683:683 + 1656, 621:621 + 2208]

        img = cv2.resize(img, dsize=size)
        video.write(img)

    # for i in range(30):
    #     video.write(img)

    video.release()


def create_sunrise_multi_timelapse(
        src_folders: list[Path],
        dst_file: Path | str,
        fps=24,
        time_per_second=60,
        single_size: Optional[tuple[int, int]] = (480, 360),
):
    n = len(src_folders)
    shape = np.asarray(as_quadratic_shape_as_possible(n))
    single_size = np.asarray(single_size)
    full_size = single_size * shape

    # Gather times and filenames
    time_dict = {}
    filepath_dict = {}
    for folder in tqdm(src_folders, desc="Gather times and filenames"):
        filepaths = [file for file in folder.iterdir() if file.is_file() and file.name.endswith(".JPG")]
        times = [
            datetime.datetime.strptime(Image.open(file)._getexif()[36867], '%Y:%m:%d %H:%M:%S').timestamp() % (
                    24 * 60 * 60)
            for file in filepaths
        ]

        filepath_dict[folder.name] = filepaths
        time_dict[folder.name] = np.asarray(times)

    # get start and end time
    min_timestamp = min([np.min(times) for times in time_dict.values()])
    max_timestamp = max([np.max(times) for times in time_dict.values()])
    delta_timestamp = max_timestamp - min_timestamp

    video_duration = delta_timestamp / time_per_second

    print(f"Creating a video of size {full_size} with a duration of {video_duration} seconds")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(str(dst_file), fourcc, fps, full_size)

    dt = time_per_second / fps

    for l, current_time in enumerate(tqdm(np.arange(min_timestamp, max_timestamp + 0.1, dt), desc="Creating video...")):
        frame = np.zeros((full_size[1], full_size[0], 3), dtype=np.uint8)
        # if l > 24*3:
        #     break
        for i, (filepaths, times) in enumerate(zip(filepath_dict.values(), time_dict.values())):
            row = i // shape[0]
            col = i % shape[0]

            image_index = np.argmin(np.abs(times - current_time))

            img = read_img(filepaths[image_index])

            img = cv2.resize(img, dsize=single_size)
            single_h = single_size[1]
            single_w = single_size[0]
            frame[row * single_h:(row + 1) * single_h, col * single_w: (col + 1) * single_w] = img

        video.write(frame)

    video.release()


def create_gluecksklee_multi_timelapse(
        src_folders: list[Path],
        dst_file: Path | str,
        fps=24,
        time_per_second=60,
        single_size: Optional[tuple[int, int]] = (480, 360),
):
    # Gather times and filenames
    time_dict = {}
    filepath_dict = {}
    for folder in tqdm(src_folders, desc="Gather times and filenames"):
        filepaths = [file for file in folder.iterdir() if file.is_file() and file.name.endswith(".jpeg")]
        times = [
            int(file.name.split("_")[1])
            for file in filepaths
        ]

        filepath_dict[folder.name] = filepaths
        time_dict[folder.name] = np.asarray(times)

    n = len(src_folders)

    # Hardcoded merge for glueckspilot and glueckspackup
    if "glueckspackup" in filepath_dict and "glueckspilot" in filepath_dict:
        filepath_dict["glueckspilot"] = filepath_dict["glueckspilot"] + filepath_dict["glueckspackup"]
        time_dict["glueckspilot"] = np.asarray(list(time_dict["glueckspilot"]) + list(time_dict["glueckspackup"]))
        filepath_dict.pop("glueckspackup")
        time_dict.pop("glueckspackup")
        n -= 1

    shape = np.asarray(as_quadratic_shape_as_possible(n))
    single_size = np.asarray(single_size)
    full_size = single_size * shape

    # get start and end time
    min_timestamp = min([np.min(times) for times in time_dict.values()])
    max_timestamp = max([np.max(times) for times in time_dict.values()])
    delta_timestamp = max_timestamp - min_timestamp

    video_duration = delta_timestamp / time_per_second

    print(f"Creating a video of size {full_size} with a duration of {video_duration} seconds")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video = cv2.VideoWriter(str(dst_file), fourcc, fps, full_size)

    dt = time_per_second / fps

    for l, current_time in enumerate(tqdm(np.arange(min_timestamp, max_timestamp + 0.1, dt), desc="Creating video...")):
        frame = np.zeros((full_size[1], full_size[0], 3), dtype=np.uint8)
        # if l > 24*3:
        #     break
        for i, (filepaths, times) in enumerate(zip(filepath_dict.values(), time_dict.values())):
            row = i // shape[0]
            col = i % shape[0]

            image_index = np.argmin(np.abs(times - current_time))

            img = read_img(filepaths[image_index])

            img = cv2.resize(img, dsize=single_size)
            single_h = single_size[1]
            single_w = single_size[0]
            frame[row * single_h:(row + 1) * single_h, col * single_w: (col + 1) * single_w] = img

        video.write(frame)

    video.release()


if __name__ == '__main__':
    source_folder = Path(
        "data/glueckspilot"
        )

    create_timelapse(
        src_folder=source_folder,
        dst_file=source_folder.parent / f"{source_folder.name}.avi",
        take_every=4,
        check_brightness=False,
        fps=30,
    )

    create_multi_timelapse(
        src_folders=[
            folder
            for folder in source_folder.parent.iterdir()
            if not folder.is_file()
        ],
        dst_file=source_folder.parent / f"multi.avi",
        time_per_second=90,
        single_size=(480 * 2, 360 * 2),
    )
