import requests
import json
import time
import os

cities = ["Lahore", "Karachi", "Islamabad", "Faisalabad", "Multan", "Peshawar", "Quetta"]
features = []

for city in cities:
    print(f"Fetching {city}...")
    try:
        url = f"https://nominatim.openstreetmap.org/search.php?q={city},+Pakistan&polygon_geojson=1&format=json"
        response = requests.get(url, headers={'User-Agent': 'AirSense-Pakistan/1.0'})
        data = response.json()
        if data:
            best_match = data[0]
            geojson = best_match.get("geojson")
            if geojson:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "name": city,
                        "display_name": best_match.get("display_name")
                    },
                    "geometry": geojson
                })
        time.sleep(1.5) # rate limit
    except Exception as e:
        print(f"Error fetching {city}: {e}")

geojson_collection = {
    "type": "FeatureCollection",
    "features": features
}

output_dir = "../frontend/public/data"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "pakistan_cities.geojson")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(geojson_collection, f)

print(f"Saved to {output_path}")
