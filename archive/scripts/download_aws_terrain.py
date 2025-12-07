import math
import requests
import os

def latlon_to_tile(lat, lon, z):
    lat_rad = math.radians(lat)
    n = 2.0 ** z
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def download_tile(lat, lon, z=12, output_dir="dted"):
    x, y = latlon_to_tile(lat, lon, z)
    url = f"https://s3.amazonaws.com/elevation-tiles-prod/geotiff/{z}/{x}/{y}.tif"
    filename = f"{output_dir}/aws_z{z}_x{x}_y{y}.tif"
    
    print(f"Downloading tile for {lat}, {lon} (Tile: {z}/{x}/{y})...")
    print(f"URL: {url}")
    
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            os.makedirs(output_dir, exist_ok=True)
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Saved to {filename}")
            return filename
        else:
            print(f"Failed: {r.status_code}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # Download a few tiles around Grand Canyon
    # Center: 36.1, -112.1
    download_tile(36.1, -112.1, z=12)
    download_tile(36.1, -112.2, z=12) # Adjacent
    
    print("\nDone! Restart the server to load these tiles.")
    print("Test coordinates: 36.1, -112.1")
