import json
import os
import time
from pathlib import Path

import eel

from . import utils
from .argument import Argument


class Data():

    PATH = './data'
    META_FILE = 'meta.json'

    def __init__(self, args, counter = {}, log = []):
        self._args = args
        self.counter = counter or Data.__counter(args.appearances)
        self.log = log
        self.start = time.perf_counter()

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

        eel.start('.', block = False)

        return eel

    def report(self):
        end = time.perf_counter()
        play_time = end - self.start

        if self._args.label is None:
            return print(f'Play time: {utils.to_time(play_time)}')

        path = os.path.join(Data.PATH, self._args.label)
        os.makedirs(path, exist_ok = True)

        path = os.path.join(path, Data.META_FILE)
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
