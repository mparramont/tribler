import sys

from threading import current_thread, local, setprofile
from time import sleep, time
from Tribler.Main.tribler import run

stats = {}
threadlocal = local()


def lock_profile(frame, event, arg):
    global stats, threadlocal

    if not hasattr(threadlocal, "lines"):
        threadlocal.lines = []

    code = frame.f_code
    filename = code.co_filename
    lineno = code.co_firstlineno

    if event in ['call', 'c_call']:
        dataline = "%.3f %s:%d" % (time(), filename, lineno)
        if dataline not in threadlocal.lines:
            threadlocal.lines.append(dataline)
            if len(threadlocal.lines) > 35:
                threadlocal.lines = threadlocal.lines[1:]

    if arg and getattr(arg, '__name__', None):
        callname = arg.__name__

        if callname in ['acquire', 'release', 'wait']:
            lockobj = arg.__self__
            if lockobj not in stats:
                stats[lockobj] = {}

            thread = current_thread()
            name = thread.getName()
            if name not in stats[lockobj]:
                stats[lockobj][name] = [sys.maxsize, sys.maxsize, sys.maxsize, sys.maxsize, sys.maxsize, sys.maxsize, False]

            index = 0
            if callname == 'release':
                index = 2
            elif callname == 'wait':
                index = 4

            if event == 'c_return':
                index += 1

            stats[lockobj][name][index] = time()
            stats[lockobj][name][6] = index == 1

            doCheck = event == 'c_return' or (event == 'c_call' and callname == 'release')
            if doCheck:
                took = stats[lockobj][name][index] - stats[lockobj][name][index - 1]
                if took > 2:
                    print("%s waited more than %.2f to %s lock %s:%d" % (name, took, callname, filename, lineno), file=sys.stderr)
                    if hasattr(threadlocal, "lines"):
                        for line in threadlocal.lines:
                            print("\t", line, file=sys.stderr)

            if index == 0:
                for otherthread in stats[lockobj]:
                    if otherthread != name:
                        if stats[lockobj][otherthread][6]:
                            print("%s waiting for lock acquired by %s" % (name, otherthread), file=sys.stderr)
                            if False and hasattr(threadlocal, "lines"):
                                for line in threadlocal.lines:
                                    print("\t", line, file=sys.stderr)

if __name__ == '__main__':
    sys.setprofile(lock_profile)
    setprofile(lock_profile)

    run()
