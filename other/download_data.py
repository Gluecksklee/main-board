from concurrent.futures import ThreadPoolExecutor, Future
from multiprocessing import Pool as mPool
from pathlib import Path

import pysftp
import tqdm

ips = {
    "glueckspilot": "192.168.178.101",
}
USER = 'root'
PASSWORD = "root_password"
LOCAL_DOWNLOAD_FOLDER = Path("local_download")


def download_data(hostname: str):
    ip = ips[hostname]
    print(f"Downloading data for {hostname} from {ip}")

    with pysftp.Connection(ip, username=USER, password=PASSWORD) as sftp:
        files = sftp.listdir("/download")
        print(f"{hostname}: {len(files)} files found")
        with sftp.cd("/download"):
            p = tqdm.tqdm(desc=hostname, unit="files", total=len(files))
            jobs: list[Future] = []
            with ThreadPoolExecutor(10) as thread_pool:
                for file in files:
                    jobs.append(thread_pool.submit(download_file_if_not_exists, sftp, hostname, f"/download/{file}"))

            for job in jobs:
                job.result(100)
                p.update(1)

    p.close()


def download_file_if_not_exists(sftp: pysftp.Connection, hostname: str, filename: str):
    remote_path = Path(filename)
    local_path = LOCAL_DOWNLOAD_FOLDER / hostname / remote_path.suffix.strip(".") / remote_path.name
    if local_path.exists():
        return

    local_path.parent.mkdir(exist_ok=True, parents=True)
    sftp.get(filename, str(local_path), preserve_mtime=True)


if __name__ == '__main__':
    with mPool() as mpool:
        mpool.map(download_data, list(ips.keys()))
