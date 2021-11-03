import argparse
import datetime
import difflib
import json
import math
import os
import re
import time
from pathlib import Path

import cv2
import numpy as np
import pyocr
import pyocr.builders
from mss import mss
from PIL import Image
from screeninfo import get_monitors

0+-+-+-+-+-+-+-+-+-+-+-+-+-+-0

DATA_PATH = 'data'
META_FILE = 'meta.json'

TYPE_WILD = 'wild'
TYPE_WILD_SYMBOL = 'wild.symbol'
TYPE_WILD_RANDOM = 'wild.random'

RATE_WILD_BREAK = 50
RATE_WILD_SYMBOL = 90
RATE_WILD_RANDOM = 190

CAPTURE_TYPE_SCREEN = 'screen'
CAPTURE_TYPE_VIDEO = 'video'

0+-+-+-+-+-+-+-+-+-+-+-+-+-+-0

def get_args():
    parser = argparse.ArgumentParser()

    help = 'Specify the existing data'
    parser.add_argument('--load', help = help)

    help = 'To save the data this time, specify the label'
    parser.add_argument('-l', '--label', help = help, default = argparse.SUPPRESS)

    help = 'Specify the type of capture'
    choices = [CAPTURE_TYPE_SCREEN, CAPTURE_TYPE_VIDEO]
    parser.add_argument('-ct', '--capture-type', choices = choices, help = help, default = argparse.SUPPRESS)

    help = 'Specify the capture target by number'
    parser.add_argument('-cn', '--capture-number', help = help, type = int, default = argparse.SUPPRESS)

    help = 'Specify the type of encounter'
    choices = [TYPE_WILD, TYPE_WILD_SYMBOL, TYPE_WILD_RANDOM]
    parser.add_argument('-t', '--type', choices = choices, help = help, default = argparse.SUPPRESS)

    help = 'Specify the Pokémon name to be counted (multiple names can be specified using single-byte spaces)'
    parser.add_argument('-a', '--appearances', nargs='*', help = help, default = argparse.SUPPRESS)

    return parser.parse_args()

def init_args(args):
    args = argparse.Namespace(**vars(args))
    _args = vars(args)

    if 'label' not in args: _args['label'] = None
    if 'capture_type' not in args: _args['capture_type'] = CAPTURE_TYPE_SCREEN
    if 'capture_number' not in args: _args['capture_number'] = 0
    if 'type' not in args: _args['type'] = TYPE_WILD
    if 'appearances' not in args: _args['appearances'] = []

    return args

0+-+-+-+-+-+-+-+-+-+-+-+-+-+-0

def main():
    start = time.perf_counter()
    args = get_args()

    if args.load:
        args, counter = load(args)
    else:
        args = init_args(args)
        counter = { name: 0 for name in args.appearances }

    display(counter)

    akaze = cv2.AKAZE_create()
    templates = get_templates(args.type, akaze)
    capture_meta = get_capture_meta(args.capture_type, args.capture_number)

    try:
        def init(): return (None, None), []
        current, compares = init()
        while True:
            time.sleep(1)

            frame = get_capture(capture_meta)
            frame = format_img(frame)
            frame_kp, frame_des = akaze.detectAndCompute(frame, None)

            if frame_des is None: continue

            matches, current = get_template_matches(templates, current, frame_des)

            if current[1] is None: continue
            elif len(matches) < current[1]:
                if not len(compares): continue
                # Do
            else:
                compare = { 'img': frame, 'kp': frame_kp, 'matches': matches }
                compares.append(compare)
                continue

            template = current[0]
            compare = max(compares, key = lambda compare: len(compare['matches']))
            frame_target = extract_kps_target(template, compare)

            rate, name = what_pokemon(frame_target, args.appearances)

            if rate > .75:
                counter[name] += 1
                display(counter)

            current, compares = init()
    except (KeyboardInterrupt, Exception) as e:
        print('\n')
        if str(e): print(f'Error: {e}')
    finally:
        capture_release(capture_meta)
        report(args, counter, start)

0+-+-+-+-+-+-+-+-+-+-+-+-+-+-0

def deep_merge(d1, d2, duplicate = True):
    d = {}

    for k, v in d1.items():
        if k in d2:
            if type(v) is dict: d[k] = merge(d1[k], d2[k], duplicate)
            elif type(v) is list:
                if type(d2[k]) is not list: d2[k] = [d2[k]]
                d[k] = d1[k] + d2[k]
                if not duplicate: d[k] = list(dict.fromkeys(d[k]))
            else:
                d[k] = d2[k]
        else:
            d[k] = d1[k]

    for k, v in d2.items():
        if k not in d1: d[k] = d2[k]

    return d

def to_time(ss):
    ss = math.floor(ss)
    m, _ = divmod(ss, 60)
    h, m = divmod(m, 60)
    return f'{h}:{str(m).zfill(2)}'

0+-+-+-+-+-+-+-+-+-+-+-+-+-+-0

def load(args):
    path = os.path.join(DATA_PATH, args.load, META_FILE)
    with open(path, 'r', encoding = "utf-8") as f:
        meta = f.read() or '{}'
        meta = json.loads(meta)

        meta_args = meta.get('args', {})
        meta_counter = meta.get('counter', {})

        args = deep_merge(meta_args, vars(args), duplicate = False)
        args = argparse.Namespace(**args)
        counter = { name: 0 for name in args.appearances }
        counter = counter | meta_counter

    return args, counter

def get_capture_meta(type, n):
    if CAPTURE_TYPE_VIDEO == type: capture = cv2.VideoCapture(n)
    else: capture = get_monitor(n)
    return type, capture

def get_capture(meta):
    type, capture = meta

    if CAPTURE_TYPE_VIDEO == type:
        _, frame = capture.read()
    else:
        with mss() as sct:
            frame = sct.grab(capture)
            frame = np.asarray(frame)

    return frame

def capture_release(meta):
    type, capture = meta

    if CAPTURE_TYPE_VIDEO == type:
        capture.release()
        cv2.destroyAllWindows()

def get_templates(type, akaze):
    list = []

    if type in TYPE_WILD_SYMBOL: list.append(TYPE_WILD_SYMBOL)
    if type in TYPE_WILD_RANDOM: list.append(TYPE_WILD_RANDOM)

    for i, type in enumerate(list):
        img = cv2.imread(f'./assets/images/{type}.jpg')
        img = format_img(img)
        kp, des = akaze.detectAndCompute(img, None)
        list[i] = { 'type': type, 'img': img, 'kp': kp, 'des': des }

    return list

def display(counter):
    print(f'\rCounter: {counter}', end = '')

def format_img(img, scale = 1):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, None, interpolation = cv2.INTER_LINEAR, fx = scale, fy = scale)
    return img

def get_monitor(i):
    m = get_monitors()[i]
    return { "top": m.y, "left": m.x, "width": m.width, "height": m.height }

def get_frame(i):
    monitor = get_monitor(i)
    with mss() as sct: frame = sct.grab(monitor)
    return np.asarray(frame)

def get_template_matches(templates, current, frame_des):
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    list = []

    for template in templates:
        if current[0] and current[0]['type'] != template['type']: continue

        matches = bf.knnMatch(template['des'], frame_des, k = 2)
        try: matches = [m for m, n in matches if m.distance < .5 * n.distance]
        except Exception: list.append([]); continue
        list.append(matches)

        matches_length = len(matches)
        if matches_length < RATE_WILD_BREAK: break
        if TYPE_WILD_SYMBOL == template['type'] and matches_length > RATE_WILD_SYMBOL:
            current = (template, RATE_WILD_SYMBOL); break
        if TYPE_WILD_RANDOM == template['type'] and matches_length > RATE_WILD_RANDOM:
            current = (template, RATE_WILD_RANDOM); break

    matches = max(list, key = lambda matches: len(matches))
    return matches, current

def extract_kps_target(target, compare):
    kps_query_x = []
    kps_query_y = []
    kps_train_x = []
    kps_train_y = []

    for match in compare['matches']:
        gq = match.queryIdx
        gt = match.trainIdx

        kps_query_x.append(target['kp'][gq].pt[0])
        kps_query_y.append(target['kp'][gq].pt[1])
        kps_train_x.append(compare['kp'][gt].pt[0])
        kps_train_y.append(compare['kp'][gt].pt[1])

    x_mag = (max(kps_query_x) - min(kps_query_x)) / (max(kps_train_x) - min(kps_train_x))
    y_mag = (max(kps_query_y) - min(kps_query_y)) / (max(kps_train_y) - min(kps_train_y))

    height, width = target['img'].shape

    left = int(min(kps_train_x) - min(kps_query_x) / x_mag)
    right = int(left + width / x_mag)
    top = int(min(kps_train_y) - min(kps_query_y) / y_mag)
    bottom = int(top + height / y_mag)

    left = max(0, left)
    right = max(width, right)
    top = max(0, top)
    bottom = max(height, bottom)

    return compare['img'][top:bottom, left:right]

def what_pokemon(img, appearances):
    img = Image.fromarray(img)

    tool = pyocr.get_available_tools()[0]
    builder = pyocr.builders.TextBuilder(tesseract_layout=6)
    txt = tool.image_to_string(img, lang='jpn', builder=builder)
    txt = re.sub(r'\s', '', txt.split('\n')[1])
    name = txt.rsplit('が', 1)[0]

    result = [(difflib.SequenceMatcher(None, _name, name).ratio(), _name) for _name in appearances]
    result = max(result, key=lambda item: item[0])

    return result

def report(args, counter, start):
    end = time.perf_counter()
    play_time = end - start

    if args.label is None:
        return print(f'Play time: {to_time(play_time)}')

    path = os.path.join(DATA_PATH, args.label)
    os.makedirs(path, exist_ok = True)

    path = os.path.join(path, META_FILE)
    path = Path(path)
    path.touch(exist_ok = True)

    with open(path, 'r+', encoding = "utf-8") as f:
        meta = f.read() or '{}'
        meta = json.loads(meta)

        play_time = meta.get('play_time', 0) + play_time
        meta['play_time'] = play_time
        meta['args'] = meta.get('args', {}) | vars(args)
        meta['counter'] = meta.get('counter', {}) | counter

        meta = json.dumps(meta, indent = 2, ensure_ascii = False)

        f.truncate(0)
        f.seek(0)
        f.write(meta)

        print(f'Play time: {to_time(play_time)}')
        print('You saved your progress!')

0+-+-+-+-+-+-+-+-+-+-+-+-+-+-0

main()
