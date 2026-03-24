You are reviewing several second-order series RLC filter stages from a lab notebook. Each CSV row describes one stage with exact component values and tells you which component voltage is taken as the output.

Write a Python script at:

`/root/workspace/rlc_symbolic_response.py`

The script must expose the function:

```python
def analyze_rlc_filters(filepath: str) -> dict:
```

The evaluation input file is:

`/root/filter_bank/rlc_filter_bank.csv`

Each row has these columns:

- `filter_id`
- `output_probe` (`capacitor`, `resistor`, or `inductor`)
- `R_ohm`
- `L_henry`
- `C_farad`

Requirements:

1. Read every row in the CSV file and preserve the row order in the returned result.
2. Treat all listed component values as exact rational quantities. Do not convert them to floating-point approximations.
3. For a series RLC driven by `Vin`, derive the voltage transfer function `H(s) = Vout(s) / Vin(s)` for the requested output probe.
4. Report the transfer function using the symbol `s`, with numerator and denominator written as simplified polynomial strings whose denominator has constant term `1`.
5. For each filter, return:
   - `numerator_polynomial`
   - `denominator_polynomial`
   - `transfer_function`
   - `poles`
   - `damping_class`
   - `dc_limit`
   - `high_frequency_limit`
6. Use exact symbolic poles. Do not replace them with decimal approximations.
7. Classify the damping only from the denominator polynomial and use one of:
   - `underdamped`
   - `critically_damped`
   - `overdamped`
8. Return the result in this shape:

```python
{
    "filters": {
        "<filter_id>": {
            "numerator_polynomial": "s",
            "denominator_polynomial": "2*s**2 + s + 1",
            "transfer_function": "s/(2*s**2 + s + 1)",
            "poles": [
                "-1/4 - sqrt(7)*I/4",
                "-1/4 + sqrt(7)*I/4"
            ],
            "damping_class": "underdamped",
            "dc_limit": "0",
            "high_frequency_limit": "0"
        }
    }
}
```

9. Do not hardcode the expected answers. Parse the CSV input and compute the symbolic response data from the listed component values.
