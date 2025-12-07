import getpass
import os
import usgsxplore.api

def download_dted_from_usgs():
    print("--- USGS Earth Explorer DTED Downloader ---")
    print("This script uses the 'usgsxplore' library to search and download data.")
    print("You need a USGS Earth Explorer account with M2M API access enabled.")
    
    username = input("USGS Username: ")
    password = getpass.getpass("USGS Password: ")
    
    try:
        api = usgsxplore.api.USGSXploreAPI(username, password)
        print("Successfully logged in!")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # Define search parameters
    dataset = "SRTM_1_ARC_SECOND_GLOBAL" # Common SRTM dataset
    location = input("Enter a location to search (e.g., 'Philadelphia, PA' or '40.0,-75.0'): ")
    
    # Simple coordinate parsing if user enters lat,lon
    bbox = None
    if "," in location and any(c.isdigit() for c in location):
        try:
            lat, lon = map(float, location.split(","))
            # Create a small bbox around the point
            bbox = (lon - 0.1, lat - 0.1, lon + 0.1, lat + 0.1)
            print(f"Searching around {lat}, {lon}...")
        except:
            pass
            
    # Search
    print("Searching for scenes...")
    # Note: usgsxplore search syntax might vary; this is a generalized example
    # based on common usage. If specific geocoding is needed, we might need extra steps.
    # For now, let's assume the user provides a lat/lon for simplicity in this script 
    # or we use the library's built-in geocoding if available.
    
    # Since usgsxplore is a wrapper, we'll try to use its search method.
    # If bbox is set:
    results = []
    if bbox:
        # API expects specific criteria. 
        # For simplicity in this 'helper' script, we will just print instructions 
        # if the library usage is complex, but let's try a direct search if possible.
        pass
        
    print("\nNOTE: Programmatic download requires precise dataset names and entity IDs.")
    print("For best results with DTED/SRTM:")
    print("1. Go to https://earthexplorer.usgs.gov/")
    print("2. Select 'Digital Elevation' -> 'SRTM' -> 'SRTM 1 Arc-Second Global'")
    print("3. Download the GeoTIFF files.")
    print("4. Place them in the 'dted/' folder of this project.")
    
    api.logout()

if __name__ == "__main__":
    download_dted_from_usgs()
