You are given a preconditioned single-detector compact-binary candidate segment and the corresponding one-sided PSD. The strain samples are in `/root/data/conditioned_strain.csv` with columns `time_s,strain`, and the PSD samples are in `/root/data/noise_psd.csv` with columns `frequency_hz,psd`.

Using these provided inputs directly, scan a template bank for the approximants `"SEOBNRv4_opt"`, `"IMRPhenomD"`, and `"TaylorT4"` over the mass grid:

- `mass1` in `{14, 16, ..., 34}` solar masses
- `mass2` in `{14, 16, ..., 34}` solar masses
- only evaluate combinations with `mass1 >= mass2`

For each approximant, find the template that gives the largest matched-filter SNR against the candidate strain. Report:

- `approximant`: waveform approximant name
- `snr`: peak absolute SNR for the best template
- `total_mass`: `mass1 + mass2` for that best template
- `peak_time`: the sample time in seconds at which that peak SNR occurs

Write the result to `/root/compact_binary_template_bank_scan.csv` with exactly these columns:

```csv
approximant,snr,total_mass,peak_time
```

Return one row per approximant and sort the rows by `approximant`.
