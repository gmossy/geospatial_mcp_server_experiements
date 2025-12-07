import numpy as np
import rasterio
from rasterio.transform import from_origin
import os

def generate_synthetic_dem(filename="dted/dem.tif", lat_min=40.0, lon_min=-75.0, size=1000):
    """
    Generates a synthetic GeoTIFF DEM with a simple hill.
    """
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # 1 arc-second approx (0.000277 degrees)
    res = 0.000277
    transform = from_origin(lon_min, lat_min + (size * res), res, res)
    
    # Create some terrain: a hill in the center
    x = np.linspace(-10, 10, size)
    y = np.linspace(-10, 10, size)
    X, Y = np.meshgrid(x, y)
    R = np.sqrt(X**2 + Y**2)
    Z = np.sin(R) * 500 + 500  # Elevation 0 to 1000m
    
    # Add some noise
    Z += np.random.normal(0, 10, Z.shape)
    
    Z = Z.astype(np.float32)
    
    with rasterio.open(
        filename,
        'w',
        driver='GTiff',
        height=size,
        width=size,
        count=1,
        dtype=Z.dtype,
        crs='+proj=latlong',
        transform=transform,
    ) as dst:
        dst.write(Z, 1)
        
    print(f"Generated synthetic DEM at {filename}")
    print(f"Bounds: {dst.bounds}")

if __name__ == "__main__":
    generate_synthetic_dem()
