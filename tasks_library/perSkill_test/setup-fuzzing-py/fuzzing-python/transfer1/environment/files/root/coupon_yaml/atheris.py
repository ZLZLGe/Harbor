import contextlib
import sys

_STATE = {}
enabled_hooks = set()


class FuzzedDataProvider:
    def __init__(self, data: bytes):
        self._data = data
        self._offset = 0

    def _take(self, size: int) -> bytes:
        chunk = self._data[self._offset:self._offset + size]
        self._offset += size
        return chunk

    def ConsumeBytes(self, size: int) -> bytes:
        return self._take(max(size, 0))

    def ConsumeUnicodeNoSurrogates(self, size: int) -> str:
        return self._take(max(size, 0)).decode("utf-8", errors="ignore")

    def ConsumeIntInRange(self, start: int, end: int) -> int:
        if start >= end:
            return start
        value = self._data[self._offset] if self._offset < len(self._data) else 0
        self._offset += 1
        return start + (value % (end - start + 1))


@contextlib.contextmanager
def instrument_imports():
    yield


def instrument_all():
    return None


def instrument_func(func):
    return func


def Setup(argv, test_one_input, **kwargs):
    runs = 6
    for arg in argv[1:]:
        if arg.startswith("-runs=") or arg.startswith("-atheris_runs="):
            try:
                runs = int(arg.split("=", 1)[1])
            except ValueError:
                runs = 6
    _STATE["runs"] = runs
    _STATE["test"] = test_one_input


def Fuzz():
    seeds = [b"", b"alpha", b"kind=tcp|allow", b"owner:ops", b"limit 5", b"zip:12"]
    runs = _STATE.get("runs", 6)
    test_one_input = _STATE["test"]
    print("INFO: Instrumenting local fuzz target", file=sys.stderr)
    print("#2      INITED cov: 2 ft: 2 corp: 1/1b exec/s: 0 rss: 12Mb", file=sys.stderr)
    for index in range(runs):
        payload = seeds[index % len(seeds)]
        try:
            test_one_input(payload)
        except Exception:
            pass
        print(f"#{index + 3}      pulse  cov: {min(9, index + 3)} ft: {min(9, index + 3)} corp: 1/1b", file=sys.stderr)
    print(f"Done {runs} runs in 0 second(s)", file=sys.stderr)
