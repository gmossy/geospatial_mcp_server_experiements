import elevation
import os

def download_sample_data():
    # Mt. Rainier area (interesting terrain)
    # Bounds: min_lon, min_lat, max_lon, max_lat
    bounds = (-121.9, 46.7, -121.6, 47.0)
    output = "dted/rainier.tif"
    
    print(f"Downloading SRTM data for Mt. Rainier to {output}...")
    print("This pulls from public caches (OpenTopography/USGS)...")
    
    os.makedirs("dted", exist_ok=True)
    
    # clip() downloads and crops the data
    elevation.clip(bounds=bounds, output=output)
    
    # Clean up temporary cache if desired
    elevation.clean()
    
    print("Done! You can now use tools with coordinates around 46.85, -121.76")

if __name__ == "__main__":
    download_sample_data()
