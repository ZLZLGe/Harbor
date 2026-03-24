import math
import os

import numpy as np


DATA_DIR = "/app/data"
OUTPUT_DIR = "/app"


def norm_cdf(x):
    erf = np.vectorize(lambda z: math.erf(z / math.sqrt(2.0)), otypes=[np.float64])
    return 0.5 * (1.0 + erf(x))


def load_inputs():
    book = np.load(os.path.join(DATA_DIR, "portfolio_book.npz"))
    grid = np.load(os.path.join(DATA_DIR, "scenario_grid.npz"))
    return book, grid


def portfolio_value(book, spot, vol_shift, rate_shift):
    strike = book["strike"].astype(np.float64)
    tau = book["maturity_years"].astype(np.float64)
    sigma = book["base_vol"].astype(np.float64) + book["vol_beta"].astype(np.float64) * vol_shift
    rate = book["base_rate"].astype(np.float64) + rate_shift
    option_type = book["option_type"].astype(np.float64)
    quantity = book["quantity"].astype(np.float64)

    sqrt_tau = np.sqrt(tau)
    d1 = (np.log(spot / strike) + (rate + 0.5 * sigma * sigma) * tau) / (sigma * sqrt_tau)
    d2 = d1 - sigma * sqrt_tau
    prices = option_type * (
        spot * norm_cdf(option_type * d1)
        - strike * np.exp(-rate * tau) * norm_cdf(option_type * d2)
    )
    return float(np.sum(quantity * prices))


def first_derivative(func, x, h):
    return (func(x + h) - func(x - h)) / (2.0 * h)


def second_derivative(func, x, h):
    return (func(x + h) - 2.0 * func(x) + func(x - h)) / (h * h)


def expected_columns():
    book, grid = load_inputs()
    spots = grid["spot"].astype(np.float64)
    vol_shifts = grid["vol_shift"].astype(np.float64)
    rate_shifts = grid["rate_shift"].astype(np.float64)

    values = np.array(
        [portfolio_value(book, spot, vol_shift, rate_shift) for spot, vol_shift, rate_shift in zip(spots, vol_shifts, rate_shifts)],
        dtype=np.float64,
    )

    delta = np.array(
        [
            first_derivative(
                lambda s, vol_shift=vol_shift, rate_shift=rate_shift: portfolio_value(
                    book, s, vol_shift, rate_shift
                ),
                spot,
                0.1,
            )
            for spot, vol_shift, rate_shift in zip(spots, vol_shifts, rate_shifts)
        ],
        dtype=np.float64,
    )

    gamma = np.array(
        [
            second_derivative(
                lambda s, vol_shift=vol_shift, rate_shift=rate_shift: portfolio_value(
                    book, s, vol_shift, rate_shift
                ),
                spot,
                0.1,
            )
            for spot, vol_shift, rate_shift in zip(spots, vol_shifts, rate_shifts)
        ],
        dtype=np.float64,
    )

    vega = np.array(
        [
            first_derivative(
                lambda vol, spot=spot, rate_shift=rate_shift: portfolio_value(
                    book, spot, vol, rate_shift
                ),
                vol_shift,
                1e-4,
            )
            for spot, vol_shift, rate_shift in zip(spots, vol_shifts, rate_shifts)
        ],
        dtype=np.float64,
    )

    rho = np.array(
        [
            first_derivative(
                lambda rate, spot=spot, vol_shift=vol_shift: portfolio_value(
                    book, spot, vol_shift, rate
                ),
                rate_shift,
                1e-4,
            )
            for spot, vol_shift, rate_shift in zip(spots, vol_shifts, rate_shifts)
        ],
        dtype=np.float64,
    )

    return np.stack([values, delta, gamma, vega, rho], axis=1)


def test_output_file_exists_and_shape_is_correct():
    path = os.path.join(OUTPUT_DIR, "portfolio_greeks.npy")
    assert os.path.exists(path), "Missing output file: portfolio_greeks.npy"
    actual = np.load(path)
    _, grid = load_inputs()
    assert actual.shape == (grid["spot"].shape[0], 5)


def test_value_column_matches_black_scholes_aggregation():
    actual = np.load(os.path.join(OUTPUT_DIR, "portfolio_greeks.npy"))
    expected = expected_columns()
    assert np.all(np.isfinite(actual)), "Non-finite values found in portfolio_greeks.npy"
    assert np.allclose(actual[:, 0], expected[:, 0], rtol=1e-5, atol=1e-5)


def test_greek_columns_match_finite_difference_estimates():
    actual = np.load(os.path.join(OUTPUT_DIR, "portfolio_greeks.npy"))
    expected = expected_columns()
    assert np.allclose(actual[:, 1], expected[:, 1], rtol=5e-4, atol=1e-3)
    assert np.allclose(actual[:, 2], expected[:, 2], rtol=2e-3, atol=1e-4)
    assert np.allclose(actual[:, 3], expected[:, 3], rtol=5e-4, atol=1e-3)
    assert np.allclose(actual[:, 4], expected[:, 4], rtol=5e-4, atol=1e-3)


def test_long_option_portfolio_has_positive_gamma_and_vega():
    actual = np.load(os.path.join(OUTPUT_DIR, "portfolio_greeks.npy"))
    assert np.all(actual[:, 2] > 0.0)
    assert np.all(actual[:, 3] > 0.0)
