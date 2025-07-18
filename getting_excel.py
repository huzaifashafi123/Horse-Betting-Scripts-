import os
import json
import pandas as pd
import re

# Folder containing your JSON files
folder_path = r"C:\Users\Huzaifa\Desktop\equilbase\output_json"  # 🔁 Change this to your actual path

# List to store all records
all_records = []

# Helper to clean track name
def clean_track_name(track_str):
    return track_str.replace('_', ' ').title()

# Loop through all JSON files
for filename in os.listdir(folder_path):
    if filename.endswith(".json"):
        match = re.match(r"(.*?)_(\d{2}-\d{2}-\d{4})_race_(\d+)\.json", filename)
        if match:
            track_name_raw, race_date, race_number = match.groups()
            track_name = clean_track_name(track_name_raw)

            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"⚠️ Skipping {filename}: {e}")
                continue

            for record in data:
                record['track_name'] = track_name
                record['date'] = race_date
                record['race_number'] = race_number
                all_records.append(record)
# Convert all records to a DataFrame
df = pd.DataFrame(all_records)

# Save to Excel
output_path = "combined_race_data.xlsx"
df.to_excel(output_path, index=False)

print(f"✅ Combined Excel file saved to: {output_path}")
