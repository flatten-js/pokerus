import cv2
import numpy as np
from mss import mss
from screeninfo import get_monitors

from .argument import Argument


class Capture():

    def __init__(self, type, n):
        self.meta = self.__meta(type, n)

    def __monitor(self, i):
        m = get_monitors()[i]
        return { "top": m.y, "left": m.x, "width": m.width, "height": m.height }

    def __meta(self, type, n):
        if Argument.CAPTURE_TYPE_VIDEO == type: capture = cv2.VideoCapture(n)
        else: capture = self.__monitor(n)
        return type, capture

    def get(self):
        type, capture = self.meta

        if Argument.CAPTURE_TYPE_VIDEO == type:
            _, frame = capture.read()
        else:
            with mss() as sct:
                frame = sct.grab(capture)
                frame = np.asarray(frame)

        return frame

    def release(self):
        type, capture = self.meta

        if Argument.CAPTURE_TYPE_VIDEO == type:
            capture.release()
            cv2.destroyAllWindows()
