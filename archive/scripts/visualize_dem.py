import rasterio
import matplotlib.pyplot as plt
import numpy as np
import os

def visualize_dem(input_path="dted/dem.tif", output_path="dted/dem_preview.png"):
    if not os.path.exists(input_path):
        print(f"File not found: {input_path}")
        return

    with rasterio.open(input_path) as src:
        data = src.read(1)
        
        # Mask out nodata values if present
        if src.nodata is not None:
            data = np.ma.masked_equal(data, src.nodata)
            
        plt.figure(figsize=(10, 8))
        plt.imshow(data, cmap='terrain')
        plt.colorbar(label='Elevation (m)')
        plt.title(f"DEM Preview: {os.path.basename(input_path)}")
        plt.axis('off')
        
        plt.savefig(output_path, bbox_inches='tight', dpi=150)
        print(f"Saved preview to {output_path}")
        plt.close()

if __name__ == "__main__":
    visualize_dem()
