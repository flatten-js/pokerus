import argparse
import difflib
import re
import time

import cv2
import numpy as np
import pyocr
import pyocr.builders
from mss import mss
from PIL import Image
from screeninfo import get_monitors


def get_args():
    parser = argparse.ArgumentParser()

    help = 'Specify the encounter type'
    parser.add_argument('-t', '--type', choices = ['wild'], help = help, required = True)

    help = 'Specify the Pokémon name to be counted (multiple names can be specified using single-byte spaces)'
    parser.add_argument('-a', '--appearances', nargs='+', help = help, required = True)

    help = 'Specify the target monitors in index format'
    parser.add_argument('-m', '--monitor', help = help, default = 0)

    return parser.parse_args()

def main():
    args = get_args()

    akaze = cv2.AKAZE_create()

    target_img = cv2.imread(f'./assets/images/{args.type}.jpg')
    target_img = format_img(target_img)
    target_kp, target_des = akaze.detectAndCompute(target_img, None)

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)

    compares = []
    counter = {}
    while True:
        time.sleep(.75)

        frame = get_frame(args.monitor)
        frame = format_img(frame)
        frame_kp, frame_des = akaze.detectAndCompute(frame, None)

        if frame_des is None: continue

        matches = bf.knnMatch(target_des, frame_des, k = 2)
        matches = [m for m, n in matches if m.distance < .5 * n.distance]

        if len(matches) < 80:
            if len(compares) == 0: continue
        else:
            compares.append((frame, frame_kp, matches))
            continue

        compare = max(compares, key = lambda compare: len(compare[2]))
        frame_target = extract_kps_target(target_img, target_kp, compare)

        rate, name = what_pokemon(frame_target, args.appearances)

        if rate > .75:
            counter[name] = counter.get(name, 0) + 1
            print(counter)

        compares = []


def format_img(img, scale = 1):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, None, interpolation = cv2.INTER_LINEAR, fx = scale, fy = scale)
    return img

def get_monitor(i):
    m = get_monitors()[i]
    return (m.x, m.y, m.width, m.height)

def get_frame(i):
    monitor = get_monitor(i)
    with mss() as sct: frame = sct.grab(monitor)
    return np.asarray(frame)

def extract_kps_target(target_img, target_kp, compare):
    compare_img, compare_kp, matches = compare

    kps_query_x = []
    kps_query_y = []
    kps_train_x = []
    kps_train_y = []

    for match in matches:
        gq = match.queryIdx
        gt = match.trainIdx

        kps_query_x.append(target_kp[gq].pt[0])
        kps_query_y.append(target_kp[gq].pt[1])
        kps_train_x.append(compare_kp[gt].pt[0])
        kps_train_y.append(compare_kp[gt].pt[1])

    x_mag = (max(kps_query_x) - min(kps_query_x)) / (max(kps_train_x) - min(kps_train_x))
    y_mag = (max(kps_query_y) - min(kps_query_y)) / (max(kps_train_y) - min(kps_train_y))

    height, width = target_img.shape
    left = int(min(kps_train_x) - min(kps_query_x) / x_mag)
    right = int(left + width / x_mag)
    top = int(min(kps_train_y) - min(kps_query_y) / y_mag)
    bottom = int(top + height / y_mag)

    return compare_img[top:bottom, left:right]

def what_pokemon(img, appearances):
    img = Image.fromarray(img)

    tool = pyocr.get_available_tools()[0]
    builder = pyocr.builders.TextBuilder(tesseract_layout=6)
    txt = tool.image_to_string(img, lang='jpn', builder=builder)

    txt = re.sub(r'\s', '', txt.split('\n')[1])
    name = txt.split('が')[0]

    result = [(difflib.SequenceMatcher(None, _name, name).ratio(), _name) for _name in appearances]
    result = max(result, key=lambda item: item[0])

    return result


main()
