# Battery RC Identification Model

Fit a temperature-aware first-order RC equivalent-circuit model on the training segments only.

## Parameters to identify

The unknown parameter vector is

$$
\theta = [R_{0,\mathrm{ref}}, \alpha_{R_0}, R_{1,\mathrm{ref}}, \alpha_{R_1}, C_{1,\mathrm{ref}}, \alpha_{C_1}]
$$

where the reference temperature is the `reference_temperature_c` field in the case file.

## Temperature dependence

For each sample temperature $T_k$,

$$
\begin{aligned}
R_0(T_k) &= R_{0,\mathrm{ref}} \exp(\alpha_{R_0}(T_k - T_{\mathrm{ref}})) \\
R_1(T_k) &= R_{1,\mathrm{ref}} \exp(\alpha_{R_1}(T_k - T_{\mathrm{ref}})) \\
C_1(T_k) &= C_{1,\mathrm{ref}} \exp(\alpha_{C_1}(T_k - T_{\mathrm{ref}}))
\end{aligned}
$$

## State update

For each segment, initialize the RC state as

$$
v_{rc,0} = 0
$$

and then step through the rows in order:

$$
\begin{aligned}
a_k &= \exp\left(-\frac{\Delta t_k}{R_1(T_k) C_1(T_k)}\right) \\
v_{rc,k+1} &= a_k v_{rc,k} + R_1(T_k)(1-a_k) I_k
\end{aligned}
$$

`current_a` uses the discharge-positive convention.

## Terminal-voltage model

Each row provides the measured terminal voltage `voltage_v` and the open-circuit voltage `ocv_v` corresponding to the recorded SOC. The modeled terminal voltage is

$$
\hat{V}_k = \mathrm{OCV}_k - I_k R_0(T_k) - v_{rc,k}
$$

and the residual is

$$
e_k = \hat{V}_k - V_k
$$

## Objective

Minimize the training-segment sum of squared residuals:

$$
\min_{\theta} \sum_{k \in \text{training rows}} e_k^2
$$

subject to the lower and upper bounds given in `parameter_bounds`.

After fitting, evaluate the same recurrence on the validation segments and report the requested residual metrics.
