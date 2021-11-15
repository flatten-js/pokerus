import sys
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

    pokexxx = Pokexxx(args.type, args.appearances)
    capture = Capture(args.capture_type, args.capture_number)

    try:
        eel = data.sync()

        eel.init_js(data.counter, data.log)
        while True:
            eel.sleep(args.capture_cycle)

            frame = capture.get()
            result = pokexxx.clarify(frame)
            if result is None: continue

            rate, name = result
            if rate < .75: continue

            eel.update_js(name)

    except KeyboardInterrupt: pass
    except SystemExit: pass
    except Exception as e:
        print('\n')
        if str(e): print(f'Error: {e}')

    finally:
        capture.release()
        data.report()


if __name__ == "__main__":
    main()
