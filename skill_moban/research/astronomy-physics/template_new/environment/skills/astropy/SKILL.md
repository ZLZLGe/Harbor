---
name: astropy
description: Use Astropy for astronomy and physics data analysis, especially FITS/WCS coordinate handling, celestial coordinate matching, observation times, units, photometric calculations, tables, and cosmology.
---

# Astropy Astronomy Workflow

Use this skill when a task involves FITS images, WCS headers, sky coordinates, catalog cross-matching, observation times, photometry, or cosmological distances.

## Core Practices

- Read FITS files with `astropy.io.fits` and inspect the specific science HDU named by the data, not just the primary header.
- Build WCS objects with `astropy.wcs.WCS(header)` and convert detector pixels to sky coordinates with `pixel_to_world`.
- Confirm whether source extractor coordinates are FITS-style 1-based pixels. Astropy high-level WCS pixel methods use zero-based pixel coordinates, so FITS-style `(x, y)` should be converted as `(x - 1, y - 1)`.
- Keep final sky positions in ICRS unless the task explicitly asks for another frame. Use `SkyCoord` transformations for Galactic coordinates.
- Represent angular thresholds with `astropy.units`, for example `1.5 * u.arcsec`. Do not compare arcsecond thresholds against degree values without conversion.
- Use `SkyCoord.match_to_catalog_sky` or `search_around_sky` for spherical matching. Avoid Euclidean RA/Dec differences for small-angle decisions unless you have already projected and justified it.
- Use `astropy.time.Time` for observation timestamps and MJD. When the relevant observation time is the midpoint of an exposure, compute `DATE-OBS + EXPTIME / 2`.
- Use `astropy.table.Table` for ECSV and astronomy table round-trips.
- Use `astropy.cosmology` for luminosity distances and distance modulus. Preserve the cosmology name or parameters in machine-readable reports.

## Patterns

### FITS WCS to ICRS and Galactic

```python
from astropy.io import fits
from astropy.wcs import WCS

with fits.open(fits_path) as hdul:
    hdu = hdul[hdu_name]
    wcs = WCS(hdu.header)
    sky = wcs.pixel_to_world(x_pixel - 1, y_pixel - 1)
    icrs = sky.icrs
    galactic = icrs.galactic
```

### Observation Midpoint

```python
from astropy import units as u
from astropy.time import Time

start = Time(header["DATE-OBS"], scale="utc")
midpoint = start + float(header["EXPTIME"]) * u.s / 2
iso = midpoint.utc.isot
mjd = float(midpoint.utc.mjd)
```

### Angular Cross-Match

```python
from astropy import units as u
from astropy.coordinates import SkyCoord

query = SkyCoord(ra=ra_values * u.deg, dec=dec_values * u.deg, frame="icrs")
catalog = SkyCoord(ra=cat_ra * u.deg, dec=cat_dec * u.deg, frame="icrs")
idx, sep2d, _ = query.match_to_catalog_sky(catalog)
is_match = sep2d <= 1.5 * u.arcsec
sep_arcsec = sep2d.arcsec
```

### AB Magnitude and Uncertainty

For aperture flux measured over an exposure:

```python
import numpy as np

flux_rate = flux_aperture / exposure_seconds
calibrated_ab_mag = zeropoint_ab - 2.5 * np.log10(flux_rate) - extinction_mag
mag_unc = 1.0857362047581294 * flux_err / flux_aperture
```

### Cosmology Distance

```python
from astropy.cosmology import Planck18 as COSMO

luminosity_distance_mpc = float(COSMO.luminosity_distance(redshift).to_value("Mpc"))
absolute_mag = calibrated_ab_mag - float(COSMO.distmod(redshift).value)
```

## Checklist

1. Identify the correct FITS HDU and WCS.
2. Normalize detector coordinates, frame, and units before matching.
3. Convert observation times with `Time`, including exposure midpoint if required.
4. Match catalogs with spherical separations and explicit angular units.
5. Keep row-level audit columns so every final decision is traceable.
6. Make JSON summaries from the generated tables, not from duplicated hand-written counts.
