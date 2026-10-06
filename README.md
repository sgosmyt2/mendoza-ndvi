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
