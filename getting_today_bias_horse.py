import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

# Load files
csv_file = 'post_bias_outperformers.csv'
excel_file = 'equibase_today_horses_data.xlsx'

# Read both files
df_csv = pd.read_csv(csv_file)
df_excel = pd.read_excel(excel_file)

# Rename for consistency
df_csv.rename(columns={'horse_name': 'horse_name'}, inplace=True)
df_excel.rename(columns={'Horse': 'horse_name'}, inplace=True)

# Standardize name format
df_csv['horse_name_clean'] = df_csv['horse_name'].str.strip().str.lower()
df_excel['horse_name_clean'] = df_excel['horse_name'].str.strip().str.lower()

# Fuzzy match function
matched_rows = []
for idx_csv, name_csv in df_csv['horse_name_clean'].items():
    match = process.extractOne(name_csv, df_excel['horse_name_clean'], scorer=fuzz.token_sort_ratio)
    if match and match[1] >= 90:
        idx_excel = df_excel[df_excel['horse_name_clean'] == match[0]].index[0]
        combined_row = {**df_csv.loc[idx_csv].to_dict(), **df_excel.loc[idx_excel].to_dict()}
        matched_rows.append(combined_row)

# Create merged DataFrame
merged_df = pd.DataFrame(matched_rows)

# Save result
merged_df.to_csv('getting_data_to_bet_today_horses.csv', index=False)
print("✅ Fuzzy matched rows with ≥90% similarity saved to 'matched_horses.csv'")
