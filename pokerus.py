import time

import lib.utils as utils
from lib.argument import Argument
from lib.capture import Capture
from lib.data import Data
from lib.pokexxx import Pokexxx


def main():
    args = Argument.parse()

    if args.load:
        args, data = Data.load(args)
    else:
        args = Argument.to_default(args)
        data = Data(args)

    data.display()

    pokexxx = Pokexxx(args.type, args.appearances)
    capture = Capture(args.capture_type, args.capture_number)

    try:
        while True:
            time.sleep(args.capture_cycle)

            frame = capture.get()
            result = pokexxx.clarify(frame)
            if result is None: continue

            rate, name = result
            if rate < .75: continue

            data.counter[name] += 1
            data.display()

    except (KeyboardInterrupt, Exception) as e:
        print('\n')
        if str(e): print(f'Error: {e}')

    finally:
        capture.release()
        data.report()


if __name__ == "__main__":
    main()
