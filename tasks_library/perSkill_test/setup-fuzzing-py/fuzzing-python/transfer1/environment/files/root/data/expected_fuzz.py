import sys

import atheris

with atheris.instrument_imports():
    from coupon_yaml.decoder import parse_coupon_note


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    text = fdp.ConsumeUnicodeNoSurrogates(64)
    try:
        parse_coupon_note(text)
    except ValueError:
        pass


def main():
    atheris.instrument_all()
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
