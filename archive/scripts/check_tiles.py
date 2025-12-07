import rasterio
import os

def check_bounds():
    dted_dir = "dted"
    for f in os.listdir(dted_dir):
        if f.endswith(".tif"):
            path = os.path.join(dted_dir, f)
            with rasterio.open(path) as src:
                print(f"File: {f}")
                print(f"Bounds: {src.bounds}")
                print(f"CRS: {src.crs}")
                print("---")

if __name__ == "__main__":
    check_bounds()
