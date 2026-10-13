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
