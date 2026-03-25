import sys

import atheris

with atheris.instrument_imports():
    from wiretoken.parser import parse_frame


def TestOneInput(data):
    try:
        parse_frame(data)
    except ValueError:
        pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
