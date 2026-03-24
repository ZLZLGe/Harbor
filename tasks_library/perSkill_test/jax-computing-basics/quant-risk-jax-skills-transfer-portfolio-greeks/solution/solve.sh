#!/bin/bash

set -euo pipefail

python3 <<'PY'
import sys

import jax
import jax.numpy as jnp

sys.path.append("/app/skills/jax-skills")
import jax_skills as jx


book = jx.load("/app/data/portfolio_book.npz")
grid = jx.load("/app/data/scenario_grid.npz")

strike = jnp.asarray(book["strike"])
tau = jnp.asarray(book["maturity_years"])
base_vol = jnp.asarray(book["base_vol"])
vol_beta = jnp.asarray(book["vol_beta"])
base_rate = jnp.asarray(book["base_rate"])
option_type = jnp.asarray(book["option_type"])
quantity = jnp.asarray(book["quantity"])


def norm_cdf(x):
    return 0.5 * (1.0 + jax.lax.erf(x / jnp.sqrt(2.0)))


def option_price(spot, sigma, rate):
    sqrt_tau = jnp.sqrt(tau)
    d1 = (jnp.log(spot / strike) + (rate + 0.5 * sigma * sigma) * tau) / (sigma * sqrt_tau)
    d2 = d1 - sigma * sqrt_tau
    return option_type * (
        spot * norm_cdf(option_type * d1)
        - strike * jnp.exp(-rate * tau) * norm_cdf(option_type * d2)
    )


def portfolio_value(spot, vol_shift, rate_shift):
    sigma = base_vol + vol_beta * vol_shift
    rate = base_rate + rate_shift
    prices = option_price(spot, sigma, rate)
    return jnp.sum(quantity * prices)


gamma_fn = jax.grad(jax.grad(portfolio_value, argnums=0), argnums=0)


def scenario_row(spot, vol_shift, rate_shift):
    value, grads = jax.value_and_grad(portfolio_value, argnums=(0, 1, 2))(
        spot, vol_shift, rate_shift
    )
    delta, vega, rho = grads
    gamma = gamma_fn(spot, vol_shift, rate_shift)
    return jnp.stack([value, delta, gamma, vega, rho])


batched = jax.jit(jax.vmap(scenario_row))

portfolio_greeks = batched(
    jnp.asarray(grid["spot"]),
    jnp.asarray(grid["vol_shift"]),
    jnp.asarray(grid["rate_shift"]),
)

jx.save(portfolio_greeks, "/app/portfolio_greeks.npy")
PY
