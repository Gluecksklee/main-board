import cv2
import numpy as np


def _image_to_hsv(img: np.ndarray) -> np.ndarray:
    r = img[:, :, 0] / 255
    g = img[:, :, 1] / 255
    b = img[:, :, 2] / 255

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

    return np.stack([hue, saturation, value], axis=2)


def image_green_proportion(img: np.ndarray):
    gaussian = cv2.GaussianBlur(img, (5, 5), 2, 2)
    hsv = _image_to_hsv(gaussian)

    hue = hsv[:, :, 0]

    # Check color
    is_green_hue = (hue > 0.25) & (hue < 0.5)

    # Check brightness
    is_green_hue &= hsv[:, :, 1] > 0.3

    plant_percentage = np.sum(is_green_hue) / np.prod(is_green_hue.shape)
    return plant_percentage


def image_mean_brightness(img: np.ndarray) -> float:
    return np.mean(img) / 255


def imu_in_motion(
        old_vector: tuple[float, float, float],
        new_vector: tuple[float, float, float],
        threshold: float = 0.5,

) -> bool:
    acc_diff = np.linalg.norm(np.asarray(old_vector) - new_vector)
    return bool(acc_diff > threshold)


def unit_vector(vector):
    """ Returns the unit vector of the vector.  """
    return vector / np.linalg.norm(vector)


def angle_between(
        v1: tuple[float, float, float],
        v2: tuple[float, float, float]
) -> float:
    """ Returns the angle in radians between vectors 'v1' and 'v2'
    """
    v1_u = unit_vector(np.asarray(v1))
    v2_u = unit_vector(np.asarray(v2))
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))


def as_quadratic_shape_as_possible(n: int) -> tuple[int, int]:
    w = int(np.ceil(np.sqrt(n)))
    for h in range(1, w + 1):
        if h * w >= n:
            return w, h
    raise ValueError(f"Could not find valid w, h for {n} ({w=})")
