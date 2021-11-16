import difflib
import os
import re
import time

import cv2
import pyocr
import pyocr.builders
from PIL import Image

from .argument import Argument
from .capture import Capture
from .data import Data


class Pokexxx():

    def __init__(self, type, appearances):
        self.akaze = cv2.AKAZE_create()
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.templates = self.__templates(type)
        self.appearances = appearances

        self.current = None
        self.compares = []

    def __format_img(self, img, scale = 1):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.resize(img, None, interpolation = cv2.INTER_LINEAR, fx = scale, fy = scale)
        return img

    def __templates(self, type):
        types = [Argument.TYPE_WILD_SYMBOL, Argument.TYPE_WILD_RANDOM]
        templates = [_type for _type in types if type in _type]

        for i, type in enumerate(templates):
            img = cv2.imread(f'./assets/images/{type}.jpg')
            img = self.__format_img(img)
            kp, des = self.akaze.detectAndCompute(img, None)

            template = { 'type': type, 'img': img, 'kp': kp, 'des': des }
            if type == Argument.TYPE_WILD_SYMBOL: template['rate'] = Argument.RATE_WILD_SYMBOL
            elif type == Argument.TYPE_WILD_RANDOM: template['rate'] = Argument.RATE_WILD_RANDOM
            templates[i] = template

        return templates

    def __get_template_matches(self, frame_des):
        matches_list = []

        for template in self.templates:
            if self.current and self.current['type'] != template['type']: continue

            matches = self.bf.knnMatch(template['des'], frame_des, k = 2)
            try: matches = [m for m, n in matches if m.distance < .5 * n.distance]
            except Exception: matches = []; continue
            finally: matches_list.append(matches)

            matches_length = len(matches)
            if matches_length < Argument.RATE_WILD_BREAK: break
            if matches_length < Argument.RATE_WILD_RANDOM: self.current = template; break
            if matches_length < Argument.RATE_WILD_SYMBOL: self.current = template; break

        matches = max(matches_list, key = lambda matches: len(matches))
        return matches

    def __extract_kps_target(self, target, compare):
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

    def __what(self, img):
        img = Image.fromarray(img)

        tool = pyocr.get_available_tools()[0]
        builder = pyocr.builders.TextBuilder(tesseract_layout=6)
        txt = tool.image_to_string(img, lang='jpn', builder=builder)
        txt = re.sub(r'\s', '', txt.split('\n')[1])
        name = txt.rsplit('が', 1)[0]

        result = [(difflib.SequenceMatcher(None, _name, name).ratio(), _name) for _name in self.appearances]
        result = max(result, key=lambda item: item[0])

        return result

    def __snapshot(self, frame):
        frame = self.__format_img(frame)
        frame_kp, frame_des = self.akaze.detectAndCompute(frame, None)
        return frame, frame_kp, frame_des

    def __init_data(self):
        self.current = None
        self.compares = []

    def clarify(self, frame):
        _frame, frame_kp, frame_des = self.__snapshot(frame)
        if frame_des is None: return

        matches = self.__get_template_matches(frame_des)

        if self.current is None: return
        elif len(matches) < self.current['rate']:
            if not len(self.compares): return
            #Do
        else:
            compare = { 'frame': frame, 'img': _frame, 'kp': frame_kp, 'matches': matches }
            self.compares.append(compare)
            return

        template = self.current
        compare = max(self.compares, key=lambda compare: len(compare['matches']))
        frame_target = self.__extract_kps_target(template, compare)

        self.__init_data()
        return (compare['frame'], *self.__what(frame_target))
