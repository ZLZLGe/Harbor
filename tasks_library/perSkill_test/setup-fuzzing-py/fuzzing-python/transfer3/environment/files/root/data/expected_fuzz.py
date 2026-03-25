import sys

import atheris

with atheris.instrument_imports():
    from archive_header.header import decode_header


def TestOneInput(data):
    try:
        decode_header(data)
    except ValueError:
        pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
