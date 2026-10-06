# Mendoza NDVI

Cloud native Sentinel 2 pipeline that measures vegetation anomalies over the Uco Valley, Mendoza. Scenes are discovered through a STAC API and streamed as Cloud Optimized GeoTIFFs, so no imagery is ever downloaded. Uco Valley is one of Argentina's most productive agricultural regions, dependent on Andean snowmelt and highly sensitive to drought.

**Status: work in progress.**

**Stack**: Python, pystac-client, odc-stac, xarray, rioxarray, dask, geopandas, scikit-learn

## What it does

1. Searches Sentinel 2 L2A scenes over the AOI.
2. Lazily loads only the bands and window needed.
3. Masks clouds and shadows using the Sentinel 2 Scene Classification Layer.
4. Builds monthly median NDVI composites with a valid observation count.
5. Computes zscore anomalies against a per calendar month baseline climatology.
6. Exports anomaly rasters (COG) and zonal summaries (GeoParquet).

## Performance

Streaming one month (7 dates, red + NIR + SCL, ~28 x 30 km AOI) from AWS Earth Search to a laptop in Buenos Aires (Intel i5 laptop CPU, no cloud compute). Throughput is limited by network latency and bandwidth, not CPU.

| Resolution | Grid (y x x) | Workers | Time per month |
|---|---|---|---|
| 20m | 1498 x 1395 | 16 | 23s |
| 10m | 2996 x 2789 | 8 | 96s |

Worker sweep at 20m: 4 workers 72s, 8 workers 38s, 16 workers 23s, 32 workers 27s. Speedup flattens beyond 16, so 16 is the default.

Extrapolated from one month, a full 2017-2026 run should take well under 2 hours locally, so no cloud VM was needed. To be replaced with the measured total.

## Quick start

```bash
conda env create -f environment.yml
conda activate mendoza_ndvi
```

## Data

Sentinel 2 L2A from the public AWS Earth Search STAC
(`sentinel-2-l2a` collection). Contains modified Copernicus Sentinel data.
No credentials required.

## Limitations

Baseline period is 2018–2022. Cloud cover in some winter months may reduce valid observation counts. NDVI saturates over dense canopy. Not validated against ground data yet.
