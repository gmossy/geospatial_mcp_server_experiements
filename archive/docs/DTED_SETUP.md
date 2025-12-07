# Obtaining Real DTED / Elevation Data

You have two primary options for getting real elevation data:

## Option 1: USGS Earth Explorer (Recommended)
This is the most reliable source for SRTM (Shuttle Radar Topography Mission) data, which is the standard for unclassified global elevation.

1.  **Visit**: [https://earthexplorer.usgs.gov/](https://earthexplorer.usgs.gov/)
2.  **Login**: You must create a free account.
3.  **Search**:
    - Zoom to your area of interest.
    - Click "Use Map" to define the search area.
4.  **Datasets**:
    - Expand **Digital Elevation**.
    - Expand **SRTM**.
    - Check **SRTM 1 Arc-Second Global** (30m resolution).
5.  **Results**:
    - Click "Results".
    - Click the "Download Options" icon (disk) for the tiles you want.
    - Choose **GeoTIFF** format.
6.  **Install**:
    - Move the downloaded `.tif` files into the `dted/` folder of this project.
    - Restart the server.

## Option 2: NGA Maps / Public Data
The National Geospatial-Intelligence Agency (NGA) provides data, but often redirects to USGS for standard elevation products.

- **NGA GEOINT Services**: [https://www.nga.mil/resources/NGA_Maps_for_Download.html](https://www.nga.mil/resources/NGA_Maps_for_Download.html)
- **Note**: Many NGA products are in specific military formats (DTED Level 1/2 in `.dt1` or `.dt2` format).
- **Support**: This server supports `.dt1` and `.dt2` files natively via `rasterio`. If you have these files from a mission drive or NGA download, just drop them in `dted/`.

## Option 3: Programmatic Download (Advanced)
If you have a USGS M2M API key, you can use the `usgsxplore` Python library installed in this environment.
Run `python download_usgs_helper.py` to see a starter script (requires credentials).
