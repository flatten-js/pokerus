import math


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
