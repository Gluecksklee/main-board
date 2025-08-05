import datetime
import sqlite3
from pathlib import Path

import matplotlib.dates as mdates
# Following packages have to be installed additionally
# conda install pandas matplotlib seaborn
# or
# pip install pandas matplotlib seaborn
import matplotlib.pyplot as plt
import pandas as pd

labelsubstitute = {
    "internal": "cpu"
}

DATE_END = None
DATE_START = None
DATE_START = datetime.datetime(2023, 3, 12, 16, 20)
# DATE_END = datetime.datetime(2022, 12, 7)

TIME_RELATIVE = True
SHOW = True
SAVE = True
device = None


def plot_db_item(
        db,
        table,
        column,
        ax=None,
):
    ax = plt.gca() if ax is None else ax
    if DATE_START is None:
        date_start = datetime.datetime(2000, 1, 1)
    else:
        date_start = DATE_START
    if DATE_END is None:
        date_end = datetime.datetime(2100, 1, 1)
    else:
        date_end = DATE_END
    df = pd.read_sql_query(
        f"SELECT * FROM {table} WHERE time >= {date_start.timestamp()} AND time <= {date_end.timestamp()}", db)

    for name, data in df.groupby("name"):
        if TIME_RELATIVE:
            min_t = data["time"].min()
            # print(datetime.datetime.fromtimestamp(min_t) + datetime.timedelta(hours=40))
            x = [(t - min_t) / 3600 for t in data["time"]]
        else:
            x = [datetime.datetime.fromtimestamp(t) for t in data["time"]]
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.scatter(x, data[column], 2, label=labelsubstitute.get(name, name))

        print(f"Mean for {name}: {data[column].mean()}")


def print_tables(db):
    cur = db.cursor()
    stmt = f"SELECT name FROM sqlite_master WHERE type='table'"
    cur.execute(stmt)
    rows = cur.fetchall()
    print(rows)

    for row in rows:
        print(row)


def plot_temperatures(db, dst: Path | str = "plots"):
    fig = plt.figure(figsize=(8, 4.5))

    plot_db_item(db, "environmentaldata", "temperature")
    plot_db_item(db, "co2data", "temperature")
    plot_db_item(db, "internaldata", "cputemperature")
    plot_db_item(db, "o2data", "temperature")

    plt.ylim(20)
    plt.ylabel("Temperature ($\degree$C)")
    plt.xlabel("Hours since start")
    plt.legend()

    _plt_finish(Path(dst) / "Temperature.png")


def _plt_finish(filename: Path | str):
    plt.tight_layout()
    fig = plt.gcf()
    if SAVE:
        Path(filename).parent.mkdir(exist_ok=True, parents=True)
        fig.savefig(filename)
    if SHOW:
        plt.show()

    plt.close(fig)


def plot_co2(db, dst: Path | str = "plots"):
    plot_db_item(db, "co2data", "co2")
    plt.ylabel("CO$_2$ (ppm)")
    plt.xlabel("Hours since start")

    _plt_finish(Path(dst) / "co2.png")


def plot_gas(db, dst: Path | str = "plots"):
    ax1 = plt.gca()
    ax2 = ax1.twinx()
    ax2.scatter([], [])
    plot_db_item(db, "co2data", "co2", ax=ax1)
    plot_db_item(db, "o2data", "o2_ppb", ax=ax2)
    ax1.set_ylabel("CO$_2$ (ppm)")
    ax2.set_ylabel("O$_2$")
    ax1.set_xlabel("Hours since start")

    _plt_finish(Path(dst) / "gas.png")

def plot_gas_temperature(db, dst: Path | str = "plots"):
    ax1 = plt.gca()
    ax2 = ax1.twinx()
    ax2.scatter([], [])
    plot_db_item(db, "co2data", "co2", ax=ax1)
    plot_db_item(db, "o2data", "temperature", ax=ax2)
    ax1.set_ylabel("CO$_2$ (ppm)")
    ax2.set_ylabel("Temperature ($\degree$C")
    ax2.set_ylim(21, 28)
    ax1.set_xlabel("Hours since start")

    _plt_finish(Path(dst) / "gas_temperature_compare.png")


def plot_o2(db, dst: Path | str = "plots"):
    # plot_db_item(db, "o2data", "o2")
    plot_db_item(db, "o2data", "o2_ppb")
    plt.ylabel("???")
    plt.xlabel("Hours since start")
    plt.legend()

    _plt_finish(Path(dst) / "o2.png")


def plot_humidity(db, dst: Path | str = "plots"):
    plot_db_item(db, "o2data", "humidity")
    plot_db_item(db, "environmentaldata", "humidity")
    plt.ylabel("Relative humidity (%)")
    plt.xlabel("Hours since start")
    plt.legend()

    _plt_finish(Path(dst) / "humidity.png")


def plot_pressure(db, dst: Path | str = "plots"):
    plot_db_item(db, "environmentaldata", "pressure")
    plot_db_item(db, "co2data", "pressure")
    plt.ylabel("Pressure (mbar)")
    plt.xlabel("Hours since start")
    plt.legend()

    _plt_finish(Path(dst) / "pressure.png")


def plot_fantacho(db, dst: Path | str = "plots"):
    plot_db_item(db, "fantachodata", "rpm")
    plt.ylabel("RPM")
    plt.xlabel("Hours since start")
    plt.legend()
    # plt.ylim(0, 20000)

    _plt_finish(Path(dst) / "fantacho.png")


def get_latest_paths(folder: dict[str, Path | str]):
    res = {}
    for device_name, path in folder.items():
        path = Path(path)
        latest_paths = sorted([p for p in path.iterdir() if str(p.name).startswith("db")], key=lambda p: p.name)
        if len(latest_paths) == 0:
            continue

        latest = latest_paths[-1]
        res[device_name] = latest

    return res


def pressure_to_csv(db):
    if DATE_START is None:
        date_start = datetime.datetime(2000, 1, 1)
    else:
        date_start = DATE_START

    env1 = pd.read_sql_query(
        f"SELECT time, pressure FROM environmentaldata WHERE name='env1' AND time >= {date_start.timestamp()}", db)
    env2 = pd.read_sql_query(
        f"SELECT time, pressure FROM environmentaldata WHERE name='env2' AND time >= {date_start.timestamp()}", db)
    co2 = pd.read_sql_query(f"SELECT time, pressure FROM co2data WHERE time >= {date_start.timestamp()}", db)

    env1.to_csv("GLU_pressure_env1.csv")
    env2.to_csv("GLU_pressure_env2.csv")
    co2.to_csv("GLU_pressure_co2.csv")


if __name__ == '__main__':

    folders = {
        "glueckspilot": "data/glueckspilot",
    }

    paths = get_latest_paths(folders)
    for device, path in paths.items():
        print(Path(path).exists())
        conn = sqlite3.connect(path)

        print_tables(conn)
        pressure_to_csv(conn)
        plot_fantacho(db=conn)
        plot_temperatures(db=conn)
        plot_co2(db=conn)
        plot_o2(db=conn)
        plot_pressure(db=conn)
        plot_humidity(db=conn)
