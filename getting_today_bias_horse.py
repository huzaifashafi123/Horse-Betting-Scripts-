import pandas as pd

# Step 1: Load the files
csv_file = r'C:\Users\Huzaifa\Desktop\equilbase\post_bias_outperformers.csv'
excel_file = r'C:\Users\Huzaifa\Desktop\equilbase\equibase_today_horses_data.xlsx'

# Read both files
df_csv = pd.read_csv(csv_file)
df_excel = pd.read_excel(excel_file)
df_csv.rename(columns={'horse_name': 'horse_name'}, inplace=True)
df_excel.rename(columns={'Horse': 'horse_name'}, inplace=True)
# Step 2: Standardize horse name format (strip whitespace, lowercase etc.)
df_csv['horse_name'] = df_csv['horse_name'].str.strip().str.lower()
df_excel['Horse'] = df_excel['horse_name'].str.strip().str.lower()

# Step 3: Merge only matching horse names (inner join)
merged_df = pd.merge(df_csv, df_excel, on='horse_name', how='inner')

# Step 4: Save to new file (optional)
merged_df.to_csv('matched_horses.csv', index=False)

print("✅ Merged rows with matching horse names saved to 'matched_horses.csv'")
