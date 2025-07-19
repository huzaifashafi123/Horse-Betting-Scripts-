import pandas as pd
import re

# Translation map to convert superscript digits to normal digits
SUPERSCRIPT_MAP = str.maketrans({
    '⁰': '0', '¹': '1', '²': '2', '³': '3',
    '⁴': '4', '⁵': '5', '⁶': '6', '⁷': '7',
    '⁸': '8', '⁹': '9'
})

# Function to extract the first valid integer from 1 to 15
def extract_first_valid_int(text):
    if pd.isna(text):
        return None

    text = str(text)

    # Add space before superscript digits to separate them from normal digits
    text = re.sub(r'(?<=[0-9])([⁰¹²³⁴⁵⁶⁷⁸⁹])', r' \1', text)

    # Convert superscript digits to normal digits
    text = text.translate(SUPERSCRIPT_MAP)

    # Remove non-digit characters except spaces
    text = re.sub(r'[^\d\s]', ' ', text)

    # Find all digit sequences
    numbers = re.findall(r'\d+', text)

    # Return the first number between 1 and 15
    for num in numbers:
        n = int(num)
        if 1 <= n <= 15:
            return n
    return None

# Function for `pp` column: extract only first integer or drop
def extract_first_int_pp(text):
    if pd.isna(text):
        return None
    matches = re.findall(r'\d+', str(text))
    for m in matches:
        n = int(m)
        if 1 <= n <= 15:
            return n
    return None

# Load the CSV file
df = pd.read_excel("combined_race_data.xlsx")  # Replace with your actual filename

# Clean 'pp' column
df['pp'] = df['pp'].apply(extract_first_int_pp)

# Drop rows where 'pp' is NaN (i.e., no valid integer was found)
df = df.dropna(subset=['pp'])

# Convert to float or int if needed
df['pp'] = df['pp'].astype(int)

# Columns to clean
cols_to_clean = ['start', 'quarter', 'half', 'three_quarter', 'str', 'fin']

# Apply the function to clean each column
for col in cols_to_clean:
    df[col] = df[col].apply(extract_first_valid_int)

# Save the cleaned file
df.to_csv("cleaned_file.csv", index=False)

print("✅ Cleaning complete. Saved as 'cleaned_file.csv'")
