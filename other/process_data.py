import datetime
import hashlib
import json
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm
import seaborn as sns

from other.analyze_image import read_img, get_plant_percentage
from other.plot_sqlite import plot_fantacho, plot_temperatures, plot_co2, plot_o2, plot_pressure, plot_humidity, \
    plot_gas
from other.timelapse import create_timelapse, create_sunrise_multi_timelapse, create_gluecksklee_multi_timelapse
from utils.analysis import image_mean_brightness

BLACKLIST = [
    "glueckspackup"
]

# LAUNCH_DATE = datetime.datetime(2023, 3, 15, 0, 30, tzinfo=datetime.timezone.utc)
LAUNCH_DATE = None

SRC_PATH = Path("data/")
DST_PATH = Path("data_summary/")


def get_device_folders(blacklist=BLACKLIST) -> list[Path]:
    result = []
    for folder in Path(SRC_PATH).iterdir():
        if not folder.is_file() and folder.name not in blacklist:
            result.append(folder)
    return result


def analyze_images(result_file="image_analysis.csv"):
    result_file = DST_PATH / result_file

    if not result_file.exists():
        result_file.parent.mkdir(exist_ok=True, parents=True)
        result_file.write_text("device,name,value\n")

    df = pd.read_csv(result_file, header=0)

    device_folders = get_device_folders()

    for device in device_folders:
        device_name = device.name
        files = [file for file in device.iterdir() if file.name.endswith(".jpeg")]
        progressbar = tqdm(files, desc=f"Analyzing images for {device_name}")
        for image_file in progressbar:
            if image_file.name in set(df["name"]):
                continue

            progressbar.set_postfix({"fn": image_file.name})

            img = read_img(image_file.absolute())
            value = get_plant_percentage(img)

            with result_file.open("a") as d:
                d.write(f"{device_name},{image_file.name},{value}\n")


def create_timelapses(cache_file: str | Path = "timelapses.json"):
    device_folders = get_device_folders()

    cache_data = {}
    cache_file = DST_PATH / cache_file

    if cache_file.exists():
        cache_data = json.loads(cache_file.read_text())

    for device_folder in device_folders:
        device_name = device_folder.name

        print(f"Create timelapse for \"{device_name}\"")
        img_files = [
            file.name
            for file in device_folder.iterdir()
            if file.name.lower().endswith(".jpeg") or file.name.lower().endswith(".jpg")
        ]

        filehash = hashlib.sha256(",".join(img_files).encode("latin")).hexdigest()
        if cache_data.get(device_name, None) == filehash:
            print("Already in cache. SKipping...")
            continue

        create_timelapse(device_folder, DST_PATH / "timelapses" / f"timelapse_{device_name}.avi", fps=48,
                         with_timestamp=True)
        cache_data[device_name] = filehash

        # Save cache after every device
        cache_file.parent.mkdir(exist_ok=True, parents=True)
        cache_file.write_text(json.dumps(cache_data))


def update_daily_images(
        data_folder="daily_image",
        cache_file="daily_image_cache.json"
):
    # Adjust paths
    data_folder = DST_PATH / data_folder
    data_folder.mkdir(exist_ok=True, parents=True)
    cache_file = data_folder / cache_file

    # Load cache
    cache_data = {}
    if cache_file.exists():
        cache_data = json.loads(cache_file.read_text())

    def get_date(filename) -> datetime.datetime:
        date_str = filename.stem.split("_")[1]
        return datetime.datetime.fromtimestamp(int(date_str))

    # Get device folders
    device_folders = get_device_folders()
    for device_folder in device_folders:
        device_name = device_folder.name
        print(f"Update daily images for {device_name}")
        img_files = [
            file
            for file in device_folder.iterdir()
            if file.name.lower().endswith(".jpeg") or file.name.lower().endswith(".jpg")
        ]
        latest_file = cache_data.get(device_name, None)
        is_new_file = latest_file is None

        if len(img_files) == 0:
            continue

        if LAUNCH_DATE is None:
            first_date = get_date(img_files[0])
        else:
            first_date = LAUNCH_DATE
        latest_date = first_date.toordinal() - 1000  # -1000 to make the first image show up

        for file in tqdm(img_files, desc=f"Updating daily images for {device_name}"):
            is_new_file |= file.name == latest_file

            if not is_new_file:
                continue

            img = read_img(file)
            mean_brightness = image_mean_brightness(img)
            if not (0.2 < mean_brightness < 0.7):
                continue

            date = get_date(file)
            if date.toordinal() == latest_date:
                continue

            file_copy = data_folder / device_name / f"day_{date:%Y%m%d_%H%M%S}{file.suffix}"
            file_copy.parent.mkdir(exist_ok=True, parents=True)

            latest_date = date.toordinal()

            file_copy.write_bytes(file.read_bytes())

        cache_data[device_name] = img_files[-1].name

        # Update cache after every device
        cache_file.parent.mkdir(exist_ok=True, parents=True)
        cache_file.write_text(json.dumps(cache_data))


def plot_database(plot_directory: str = "plots"):
    plot_directory = DST_PATH / plot_directory

    device_folders = get_device_folders()
    for device_folder in device_folders:
        device_name = device_folder.name
        plot_device_folder = plot_directory / device_name
        print(f"Plotting database for {device_name} to {plot_device_folder}")

        databases = sorted([p for p in device_folder.iterdir() if p.name.startswith("db")], key=lambda p: p.name)
        if len(databases) == 0:
            print(f"No database for {device_name} found")
            continue

        latest_db = databases[-1]

        conn = sqlite3.connect(latest_db)

        plot_device_folder.mkdir(exist_ok=True, parents=True)
        # plot_fantacho(db=conn, dst=plot_device_folder)
        plot_sqlite.plot_gas_temperature(db=conn, dst=plot_device_folder)
        # plot_temperatures(db=conn, dst=plot_device_folder)
        # plot_gas(db=conn, dst=plot_device_folder)
        # plot_pressure(db=conn, dst=plot_device_folder)
        # plot_humidity(db=conn, dst=plot_device_folder)


def plot_green_proportion(csv: str = "image_analysis.csv", plot_direction: str = "plots"):
    df = pd.read_csv(DST_PATH / csv, header=0)
    print(df)
    df["date"] = pd.to_datetime(df["name"].str.extract(r"(\d+)").squeeze(), unit='s')
    df.drop(df[df['value'] > 0.2].index, inplace=True)
    df.drop(df[df['value'] < 0.04].index, inplace=True)

    sns.scatterplot(df, x="date", y="value", hue="device", size=1)
    plt.show()

def create_multi_timelapse(timelapse_name="timelapse_multi", cache_file:str="multi_timelapse.json"):
    device_folders = get_device_folders(blacklist=[])

    cache_data = {}
    cache_file = DST_PATH / cache_file

    if cache_file.exists():
        cache_data = json.loads(cache_file.read_text())

    # Check whether cache is okay
    cache_okay = True
    for device_folder in device_folders:
        device_name = device_folder.name
        img_files = [
            file.name
            for file in device_folder.iterdir()
            if file.name.lower().endswith(".jpeg") or file.name.lower().endswith(".jpg")
        ]

        filehash = hashlib.sha256(",".join(img_files).encode("latin")).hexdigest()
        if cache_data.get(device_name, None) == filehash:
            continue
        cache_okay = False
        print(f"{device_name} not in cache for multitimelapse")
        cache_data[device_name] = filehash

    if cache_okay:
        print("Cache for Multitimelapse already okay...")
        return

    create_gluecksklee_multi_timelapse(
        src_folders=device_folders,
        dst_file=DST_PATH / "timelapses" / f"{timelapse_name}.avi",
        time_per_second=12*60*60,
        single_size=(480 * 3, 360 * 3),
    )

    # Save cache after timelapse
    cache_file.parent.mkdir(exist_ok=True, parents=True)
    cache_file.write_text(json.dumps(cache_data))


if __name__ == '__main__':
    import plot_sqlite

    plot_sqlite.SHOW = False

    plot_database()
    update_daily_images()
    create_timelapses()
    analyze_images()
    plot_green_proportion()
    create_multi_timelapse()
    