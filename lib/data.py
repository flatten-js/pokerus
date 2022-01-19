import json
import os
import shutil
import sys
import time
from pathlib import Path

import cv2
import eel

from . import utils
from .argument import Argument


class Data():

    PATH = './data'
    TMP_FOLDER = '__tmp__'
    META_FILE = 'meta.json'

    def __init__(self, args, counter = {}, log = []):
        self.start = time.perf_counter()
        self.output = self.__output(args.load, args.label)
        self._args = args
        self.counter = counter or Data.__counter(args.appearances)
        self.log = log

    def __now_name(self):
        return str(time.time()).replace('.', '_')

    def __output(self, load, label):
        output = {}

        if label is None:
            label = Data.TMP_FOLDER
            path = os.path.join(Data.PATH, label)
            output = { '_label': label, 'label': path, 'frame': path }
            os.makedirs(path, exist_ok = True)
            return output

        try:
            output['_label'] = label
            output['label'] = os.path.join(Data.PATH, label)
            if not load: os.mkdir(output['label'])
        except FileExistsError as e:
            print(f'{type(e).__name__}: ', end = '')
            print("Please delete or '--load' the existing data with the same name.")
            sys.exit()

        output['frame'] = os.path.join(output['label'], self.__now_name())
        os.mkdir(output['frame'])

        return output

    @staticmethod
    def __counter(appearances):
        return { name: 0 for name in appearances }

    @staticmethod
    def load(args):
        path = os.path.join(Data.PATH, args.load, Data.META_FILE)
        with open(path, 'r', encoding = "utf-8") as f:
            meta = f.read() or '{}'
            meta = json.loads(meta)

            meta_args = meta.get('args', {})
            meta_counter = meta.get('counter', {})
            meta_log = meta.get('log', [])

            args = utils.deep_merge(meta_args, vars(args), duplicate = False)
            args = Argument.to_namespace(args)
            counter = Data.__counter(args.appearances)
            counter = counter | meta_counter

        return args, Data(args, counter, meta_log)

    def sync(self):
        eel.gvt.get_hub().NOT_ERROR += (KeyboardInterrupt,)

        eel.init('web/dist')

        @eel.expose
        def update_py(log): self.log = log

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

            play_time = meta.get('play_time', 0) + play_time
            meta['play_time'] = play_time
            meta['args'] = meta.get('args', {}) | vars(self._args)
            meta['counter'] = meta.get('counter', {}) | self.counter
            meta['log'] = self.log

            meta = json.dumps(meta, indent = 2, ensure_ascii = False)

            f.truncate(0)
            f.seek(0)
            f.write(meta)

            print(f'Play time: {utils.to_time(play_time)}')
            print('You saved your progress!')
