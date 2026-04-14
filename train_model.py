import rasterio
from rasterio.mask import mask
import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib

# -----------------------------
# 1️⃣ LOAD DISTRICT
# -----------------------------
district_name = input("Enter District Name: ")

districts = gpd.read_file("C:\\Users\\Shivani\\Documents\\Kerla_districts_utm.shp"
)
district = districts[
    districts["NAME_2"].str.lower() == district_name.lower()
]

if district.empty:
    print("❌ District not found!")
    exit()

print("✅ District Found:", district_name)

# -----------------------------
# 2️⃣ LOAD RASTERS
# -----------------------------
dem = rasterio.open("C:\\Users\\Shivani\\dem_utm.tif")
slope = rasterio.open("C:\\Users\\Shivani\\Downloads\\Reprojected_slope.tif")
rain = rasterio.open("C:\\Users\\Shivani\\Downloads\\rainfall_aligned_full..tif")

# Ensure CRS match
district = district.to_crs(dem.crs)

# -----------------------------
# 3️⃣ CLIP ALL RASTERS SAME WAY
# -----------------------------
dem_clip, transform = mask(dem, district.geometry, crop=True)
slope_clip, _ = mask(slope, district.geometry, crop=True)
rain_clip, _ = mask(rain, district.geometry, crop=True)

dem_data = dem_clip[0]
slope_data = slope_clip[0]
rain_data = rain_clip[0]

# -----------------------------
# 4️⃣ CREATE FLOOD LABELS (Improved – Less Perfect)
# -----------------------------

# Add controlled randomness
noise = np.random.rand(*dem_data.shape)

flood_label = (
    (dem_data < 6 + noise * 2) &
    (rain_data > 1400 + noise * 200) &
    (slope_data < 6 + noise * 2)
).astype(int)

# -----------------------------
# 5️⃣ STACK FEATURES
# -----------------------------
features = np.stack([dem_data, slope_data, rain_data], axis=-1)

# Remove NaN values
mask_valid = (
    ~np.isnan(dem_data) &
    ~np.isnan(slope_data) &
    ~np.isnan(rain_data)
)

X = features[mask_valid]
y = flood_label[mask_valid]

print("Total training samples:", len(y))
print("Flood samples:", np.sum(y))
print("Non-flood samples:", len(y) - np.sum(y))

# -----------------------------
# 6️⃣ TRAIN-TEST SPLIT
# -----------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# -----------------------------
# 7️⃣ TRAIN RANDOM FOREST
# -----------------------------
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=15,
    class_weight="balanced",
    random_state=42
)

model.fit(X_train, y_train)

# -----------------------------
# 8️⃣ EVALUATE
# -----------------------------
y_pred = model.predict(X_test)

print("\nModel Accuracy:", accuracy_score(y_test, y_pred))
print("\nClassification Report:\n")
print(classification_report(y_test, y_pred))

# -----------------------------
# 9️⃣ SAVE MODEL
# -----------------------------
joblib.dump(model, r"C:\\Users\\Shivani\\OneDrive\\Desktop\\floodApp\\flood_model.pkl")

print("\n✅ Model Trained and Saved Successfully!")
# -----------------------------
# 🔟 GENERATE FLOOD RISK MAP
# -----------------------------

print("Generating flood prediction raster...")

# Predict for all valid pixels
full_features = np.stack([dem_data, slope_data, rain_data], axis=-1)
full_X = full_features[mask_valid]

predictions = model.predict(full_X)

# Create empty raster
flood_map = np.zeros(dem_data.shape)
flood_map[mask_valid] = predictions

# Save raster
with rasterio.open(
    r"C:\\Users\\Shivani\\OneDrive\\Desktop\\flood_prediction2.tif",
    "w",
    driver="GTiff",
    height=flood_map.shape[0],
    width=flood_map.shape[1],
    count=1,
    dtype=flood_map.dtype,
    crs=dem.crs,
    transform=transform,
) as dst:
    dst.write(flood_map, 1)

print("✅ Flood prediction raster saved!")