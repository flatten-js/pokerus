import itertools
import json
import os
import shutil
import sys
import time
from pathlib import Path

import cv2
import eel
from humanize import naturalsize

from . import utils
from .argument import Argument


class Data():

    PATH = os.path.join(utils.lib_path, '../data')
    TMP_FOLDER = '__tmp__'
    FRAMES_FOLDER = 'frames'
    META_FILE = 'meta.json'

    def __init__(self, args, sys = {}, logs = []):
        self.start = time.perf_counter()
        self.output = self.__output(args.load, args.label)
        self.args = args
        self.sys = sys
        self.logs = logs

    def __now_name(self):
        return str(time.time()).replace('.', '_')

    def __output(self, load, label):
        output = {}

        if label is None: label = Data.TMP_FOLDER
        try:
            output['_label'] = label
            output['label'] = os.path.join(Data.PATH, label)
            if not load: os.mkdir(output['label'])
        except FileExistsError as e:
            print(f'{type(e).__name__}: ', end = '')
            print("Please delete or '--load' the existing data with the same name.")
            sys.exit()

        output['frame'] = os.path.join(output['label'], Data.FRAMES_FOLDER)
        os.makedirs(output['frame'], exist_ok = True)

        return output

    @staticmethod
    def load(args):
        path = os.path.join(Data.PATH, args.load, Data.META_FILE)
        with open(path, 'r', encoding = "utf-8") as f:
            meta = f.read() or '{}'
            meta = json.loads(meta)

            meta_sys = meta.get('sys', {})
            meta_args = meta.get('args', {})
            meta_logs = meta.get('logs', [])

            args = utils.deep_merge(meta_args, vars(args), duplicate = False)
            args = Argument.to_namespace(args)

        return args, Data(args, meta_sys, meta_logs)

    @staticmethod
    def list():
        datas = []

        for f in os.listdir(Data.PATH):
            f_path = os.path.join(Data.PATH, f)
            if not os.path.isdir(f_path): continue

            args = Argument.to_namespace({ 'load': f })
            args, data = Data.load(args)

            size = naturalsize(utils.folder_size(f_path))

            datas.append({
                'name': f,
                'play_time': data.sys['play_time'],
                'updated_at': data.sys['updated_at'],
                'size': size
            })

        return datas

    def sync(self):
        eel.gvt.get_hub().NOT_ERROR += (KeyboardInterrupt,)

        eel.init('web/dist')

        @eel.expose
        def init_py():
            return { 'appearances': self.args.appearances, 'logs': self.logs }

        @eel.expose
        def update_py(logs):
            self.logs = logs
            eel.sync_js(logs)

        eel.start('.', block = False, spa = True)

        return eel

    def __resize(self, img, width):
        h, w = img.shape[:2]
        width = width or w
        height = round(h * (width / w))
        return cv2.resize(img, dsize = (width, height))

    def save_frame(self, frame, width):
        frame = self.__resize(frame, width)
        filename = f'{self.__now_name()}.jpg'
        path = os.path.join(self.output['frame'], filename)
        cv2.imwrite(path, frame)
        return path

    def report(self):
        end = time.perf_counter()
        play_time = end - self.start

        if self.output['_label'] == Data.TMP_FOLDER:
            shutil.rmtree(self.output['label'])
            return print(f'Play time: {utils.to_time(play_time)}')

        path = os.path.join(self.output['label'], Data.META_FILE)
        path = Path(path)
        path.touch(exist_ok = True)

        with open(path, 'r+', encoding = "utf-8") as f:
            meta = f.read() or '{}'
            meta = json.loads(meta)

            meta_sys = meta.get('sys', {})
            meta_sys['updated_at'] = time.time()
            meta_sys['play_time'] = meta_sys.get('play_time', 0) + play_time
            meta['sys'] = meta_sys
            meta['args'] = meta.get('args', {}) | vars(self.args)
            meta['logs'] = self.logs

            meta = json.dumps(meta, indent = 2, ensure_ascii = False)

            f.truncate(0)
            f.seek(0)
            f.write(meta)

            print(f'Play time: {utils.to_time(play_time)}')
            print('You saved your progress!')
