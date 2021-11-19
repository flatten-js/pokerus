import argparse


class Argument():

    TYPE_WILD = 'wild'
    TYPE_WILD_SYMBOL = 'wild.symbol'
    TYPE_WILD_RANDOM = 'wild.random'

    CAPTURE_TYPE_SCREEN = 'screen'
    CAPTURE_TYPE_VIDEO = 'video'

    @staticmethod
    def parse():
        parser = argparse.ArgumentParser()

        help = 'Specify the existing data'
        parser.add_argument('--load', help = help)

        help = 'To save the data this time, specify the label'
        parser.add_argument('-l', '--label', help = help, default = argparse.SUPPRESS)

        help = 'Specify the type of capture'
        choices = [Argument.CAPTURE_TYPE_SCREEN, Argument.CAPTURE_TYPE_VIDEO]
        parser.add_argument('-ct', '--capture-type', choices = choices, help = help, default = argparse.SUPPRESS)

        help = 'Specify the capture target by number'
        parser.add_argument('-cn', '--capture-number', help = help, type = int, default = argparse.SUPPRESS)

        help = 'Specifies the approximate cycle for shooting (The lower the value, the higher the load)'
        parser.add_argument('-cc', '--capture-cycle', help = help, type = float, default = argparse.SUPPRESS)

        help = 'Specify the type of encounter'
        choices = [Argument.TYPE_WILD, Argument.TYPE_WILD_SYMBOL, Argument.TYPE_WILD_RANDOM]
        parser.add_argument('-t', '--type', choices = choices, help = help, default = argparse.SUPPRESS)

        help = 'Specify the Pokémon name to be counted (multiple names can be specified using single-byte spaces)'
        parser.add_argument('-a', '--appearances', nargs='*', help = help, default = argparse.SUPPRESS)

        return parser.parse_args()

    @staticmethod
    def to_default(args):
        args = argparse.Namespace(**vars(args))
        _args = vars(args)

        if 'label' not in args: _args['label'] = None
        if 'capture_type' not in args: _args['capture_type'] = Argument.CAPTURE_TYPE_SCREEN
        if 'capture_number' not in args: _args['capture_number'] = 0
        if 'capture_cycle' not in args: _args['capture_cycle'] = 1
        if 'type' not in args: _args['type'] = Argument.TYPE_WILD
        if 'appearances' not in args: _args['appearances'] = []

        return args

    @staticmethod
    def to_namespace(args):
        return argparse.Namespace(**args)
