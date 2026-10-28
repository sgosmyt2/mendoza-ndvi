# Methods and findings (draft)

## Data
- Sentinel-2 L2A, AWS Earth Search STAC (`sentinel-2-l2a`).
- The AOI touches four MGRS tiles (19HDC, 19HDD, 19HEC, 19HED). One overpass every 5 days appears as four items, merged into one image per date by `groupby="solar_day"`.
- 2017-01 to 2026-10: 3850 items. Removed 20 non COG items and 901 superseded duplicates, leaving 2933.
- Considered `sentinel-2-c1-l2a` (no duplicates) but rejected it because no 2017 data, only 28 items in 2022, and 20 baseline months with fewer than 2 usable dates.

## Reflectance offset
- Survey: median red of SCL "not vegetated" pixels per scene, 2018-2026, at 120 m (2245 scenes measured). Unshifted scenes read ~1000-1250 DN raw (~0.11 reflectance).
- Only 24 scenes read ~1750-2250 DN: baseline 04.00, boa_offset_applied=False, acquired 2022-01-25 to 2022-02-24. These get -1000 DN before scaling.
- 92 other scenes with flag False and offset -0.1 are NOT shifted. The metadata alone would have miscorrected them.
- Not explained: why the shift is limited to that window.

## Masking
- SCL classes masked: 0, 1, 3, 8, 9, 10, and 11.
- Dilation of 2px (40 m) at 20 m resolution, chosen by eye. Not yet tested quantitatively, thinking about potentially doing so but 2px seems best.
- Classes 2 (dark areas) and 7 (unclassified) are kept; to be revisited.

## Performance
Streaming one month (7 dates, red + NIR + SCL, ~28 x 30km AOI) from AWS Earth Search to a laptop in Buenos Aires. Throughput is limited by network latency and bandwidth, not CPU.

| Resolution | Grid (y x x) | Workers | Time per month |
|---|---|---|---|
| 20m | 1498 x 1395 | 16 | 23s |
| 10m | 2996 x 2789 | 8 | 96s |

Worker sweep at 20m (March 2023): 4 workers 72s, 8 workers 38s, 16 workers 23s, 32 workers 27s. The speedup flattens beyond 16, so 16 is the default.

Extrapolated from one month, a full 2017-2026 run should take well under 2 hours locally, so no cloud VM was needed. (Estimate will be replaced with the measured total.)

## Limitations
- Scene level cloud cover describes a 110 km tile, not the AOI, so the usable dates heatmap is optimistic. Valid pixel counts are the real measure.
- The offset rule is empirical.

## Monthly composites
- 105 composites, 2018-01 to 2026-09, 20 m, EPSG:32719: median NDVI of valid pixels (`ndvi_YYYY_MM.tif`, float32) and the number of valid observations (`count_YYYY_MM.tif`, uint8).
- 5-9 dates per month. Only 12 months contain any pixels with no valid observation, and only July 2026 more than 5% (19.4%).

## Thin months
- 14 of 105 months have >= 50% of pixels under 3 valid observations: 2018-07, 2018-08, 2018-11, 2019-06, 2020-06, 2021-08, 2023-04, 2023-09, 2024-06, 2024-08,
  2025-04, 2026-06, 2026-07, 2026-08.
- 10 of the 14 are June-August. By calendar month: Jun 4, Aug 4, Jul 2, Apr 2, Sep 1, Nov 1.
- Cause (checked for Aug 2018): SCL classes 66-100% of the AOI as cloud on 4 of 6 dates, cirrus <= 8%, snow 0%. The scene level cloud figure in the catalogue (used for the usable dates heatmap) described 5 usable dates for that month, so it overstates data.
- Baseline years (2018-2022) with a usable month (< 50% thin) per calendar month: June 3/5, August 3/5, July 4/5, November 4/5, all others 5/5. Winter z-scores rest on a noisier climatology.
- 8 analysis months are thin: 2023-04, 2023-09, 2024-06, 2024-08, 2025-04, 2026-06, 2026-07, 2026-08.

## Minimum observations rule
- A pixel month is used if it has >= 2 valid observations and a pixel needs >= 4 valid baseline years for a climatology. Thin months are kept but flagged as low confidence.
- Rationale: a threshold of 3 would leave only 3 baseline years for June and August. The cost is that a thin month's composite is the mean of two images.
- To do: rerun with a threshold of 3 and compare the z-scores (sensitivity check).

## Anomaly limitations (so far)
- With a 5 year baseline, z-scores have heavy tails: simulated no change data puts ~14% of pixels beyond |z| > 2 (5th/95th percentile +-2.3). January 2023 (12.7%) and June 2024 (13.3%) are at that level while March 2024 (31.8%) is not.
- Baseline std varies from ~0.02 (bare desert) to ~0.28 (cropland, 95th pct, Mar). The std floor (0.02) binds on 6-16% of pixels. Per pixel z is not interpreted.
- Bare ground NDVI (SCL class 5, 120m scene medians, shifted window corrected) in Dec-Mar: baseline years 0.256-0.289, 2023 0.243, 2024 0.233, 2025 0.243, 2026 0.263. Cause unresolved (real soil change vs processing/instrument) so no clean step by processing baseline (05.09 0.222, 05.10 0.236, 05.11 0.235, 05.12 0.255).
- AOI median z, Feb-Mar 2023: -3.0/-3.1 raw, -2.0/-2.1 if the bare soil shift is removed.

## Stratum Sensitivity
- Strata from baseline mean NDVI of Jan-Mar. Main cut 0.3/0.4 chosen from the histogram before looking at results: bare 36%, mixed 19%, vegetated 44%.
- Cuts 0.25/0.35 and 0.35/0.45 give vegetated median z of -0.78 and -0.89 (main: -0.83). Vegetated mean z becomes more negative as the class gets purer (-0.57, -0.71, -0.87).
- The purest bare class (< 0.25) has mean z +0.09 and z std 1.63, noise alone for a 5 year baseline gives ~1.55. It has its own low episode in winter 2023.
- Analysis period summer peaks sit below the baseline band. Oct-Dec 2024 and 2025 look above it.

## Leave-one-year-out check and cause of the excess
- Baseline years scored against the other four, rms difference (NDVI): bare 0.019, mixed 0.026, vegetated 0.033 (main cuts 0.3/0.4). Analysis period against all five: 0.029 / 0.035 / 0.052 (1.35-1.6x); 25-39% of zscores beyond |z| > 2 (pure noise: 14.2%).
- Purest bare class (baseline Jan-Mar NDVI < 0.25, ~19% of AOI): analysis mean difference 0.000, rms 0.023 vs 0.018 in the baseline (1.28x), 22% beyond |z| > 2. No constant offset, the larger stratum excess at the main cut came from sparse vegetation. A modest residual excess is unexplained.
- Mean NDVI difference by calendar month (analysis period, thin months excluded, 3-4 years per cell): vegetated -0.081 (Feb), -0.073 (Mar), +0.074 (Oct); bare and mixed show the same signs at about half the size. The sign flips with the season, so a constant calibration offset is unlikely. Cause (earlier green up and lower summer peak, water availability, heat) is not established.

## Artifact check: one processing version
- 2025 was processed entirely as baseline 05.11 (349 of 349 scenes). Within that year the NDVI difference from baseline runs from -0.105 (Feb, vegetated) to +0.084 (Oct). Bare and mixed show the same signs at about half the size. A constant processing version offset cannot produce both signs, so it is ruled out.
- Not ruled out: season dependent differences between processing versions or sensors (baseline years vs 2023+). An independent sensor comparison (e.g. Landsat) would test this and it is left as future work.
- Cause of the vegetation change itself (water availability, heat, crop mix, irrigation timing) is not established.
