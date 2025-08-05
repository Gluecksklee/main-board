import math
from pathlib import Path
from typing import Union

import matplotlib.pyplot as plt
import numpy as np
import cv2
import cv2.misc
from PIL import Image
from tqdm import tqdm

SHOW_IMAGE = False





def to_hsv(img: np.ndarray) -> np.ndarray:
    r = img[:, :, 0] / 255
    g = img[:, :, 1] / 255
    b = img[:, :, 2] / 255

    show_img(r, "Red")
    show_img(g, "Green")
    show_img(b, "Blue")

    hue = np.zeros((img.shape[0], img.shape[1]))
    rgb_max = np.max(img, axis=2) / 255
    delta = rgb_max - np.min(img, axis=2) / 255
    case_r = rgb_max == r
    case_g = rgb_max == g
    case_b = rgb_max == b
    hue[case_r] = np.remainder((g - b) / delta, 6)[case_r]
    hue[case_g] = ((b - r) / delta + 2)[case_g]
    hue[case_b] = ((r - g) / delta + 4)[case_b]
    hue = np.nan_to_num(hue) / 6

    # beta = math.sqrt(3) * (g - b)
    # hue = np.arctan2(beta, alpha)
    # alpha = 2 * r - g - b
    value = rgb_max
    saturation = delta / value
    saturation = np.nan_to_num(saturation, nan=0)

    show_img(hue, "Hue")
    show_img(saturation, "Saturation")
    show_img(value, "Value")

    return np.stack([hue, saturation, value], axis=2)


def read_img(path: Union[Path, str]) -> np.ndarray:
    img1 = plt.imread(str(path))
    img1 = img1[..., ::-1]  # RGB --> BGR
    return img1


def show_img(img, name):
    if not SHOW_IMAGE:
        return
    window = cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.imshow(name, img)


def analyze(img: np.ndarray):
    gaussian = cv2.GaussianBlur(img, (5, 5), 2, 2)
    hsv = to_hsv(gaussian)
    show_img(hsv, "HSV")

    hue_min = 67.5
    hue_max = 157.5

    hue = hsv[:, :, 0]
    plt.hist(np.reshape(hue, -1), bins=100)
    plt.title("Hue")
    plt.tight_layout()
    plt.show()
    plt.hist(np.reshape(gaussian[:, :, 1], -1), bins=100)
    plt.title("Green")
    plt.tight_layout()
    plt.show()
    is_green_hue = (hue > 0.25) & (hue < 0.5)
    # is_green_hue = (hue > hue_min / 360) & (hue < hue_max / 360)
    is_green_hue &= hsv[:, :, 1] > 0.3
    mask = np.zeros_like(img)
    mask[is_green_hue] = 255
    show_img(mask, "Mask")

    fig = plt.figure(figsize=(8, 3))
    ax1 = plt.subplot(121)
    ax2 = plt.subplot(122)

    ax1.imshow(img)
    ax1.set_title("Original")
    ax2.imshow(mask)

    plant_percentage = np.sum(mask == 255) / np.prod(mask.shape)
    ax2.set_title(f"Plants: {plant_percentage * 100:.2f}%")

    plt.tight_layout()

    return fig


def get_plant_percentage(img: np.ndarray) -> float:
    gaussian = cv2.GaussianBlur(img, (5, 5), 2, 2)
    hsv = to_hsv(gaussian)
    hue = hsv[:, :, 0]
    is_green_hue = (hue > 0.25) & (hue < 0.5)
    is_green_hue &= hsv[:, :, 1] > 0.3
    mask = np.zeros_like(img)
    mask[is_green_hue] = 255

    plant_percentage = np.sum(mask == 255) / np.prod(mask.shape)
    return plant_percentage


def timelapse(folder):
    x = []
    y = []
    files = [file for file in Path(folder).iterdir() if file.is_file()]
    for file in tqdm(files):
        img = read_img(file)
        img = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)
        plant_percentage = get_plant_percentage(img)
        x.append(int(file.stem))
        y.append(plant_percentage)

    print("Save to file")
    Path("plots").mkdir(exist_ok=True, parents=True)
    with open("plots/plant_percentage.csv", "w") as d:
        for x1, y1 in zip(x, y):
            d.write(f"{x1},{y1}\n")

    plt.plot(x, y)
    plt.tight_layout()
    plt.savefig("plots/Timelapse.png")
    plt.show()


def plot_timelapse():
    xx = []
    yy = []
    with open("plots/plant_percentage.csv", "r") as d:
        for line in d:
            x, y = line.strip().split(",")
            xx.append(int(x))
            yy.append(float(y))

    xx = np.asarray(xx)
    yy = np.asarray(yy)

    mask = yy > 0.005
    xx = xx[mask]
    yy = yy[mask]

    print(f"Loaded {len(xx)} datapoints")

    plt.scatter(xx, yy, 1)
    plt.tight_layout()
    plt.ylim(0, 0.18)
    plt.savefig("plots/Timelapse.png")
    plt.show()


if __name__ == '__main__':
    test_imgs = {
        
    }
    timelapse("data/glueckspilot/images")
    plot_timelapse()
    # exit(0)
    for name, img_path in test_imgs.items():
        print(f"Name: {name}")
        img = read_img(img_path)
        show_img(img, "Original")
        fig = analyze(img)
        Path("plots").mkdir(exist_ok=True, parents=True)
        fig.savefig(f"plots/{name}.png")
        if SHOW_IMAGE:
            cv2.waitKey(0)
