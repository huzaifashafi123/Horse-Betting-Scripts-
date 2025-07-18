from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import pandas as pd
from urllib.parse import urlparse, parse_qs
from datetime import datetime

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--no-sandbox")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-session-crashed-bubble")
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--start-maximized")
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-gpu")
    driver = uc.Chrome(options=options)
    return driver

def scrape_equibase_table(url, output_filename="equibase_data.xlsx"):
    driver = get_driver()
    
    try:
        # Navigate to the URL
        driver.get(url)
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 10)
        
        # Find the table with the specified class
        table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table-padded")))
        
        # Get the header row
        thead = table.find_element(By.TAG_NAME, "thead")
        header_row = thead.find_element(By.TAG_NAME, "tr")
        headers = [th.text.strip() for th in header_row.find_elements(By.TAG_NAME, "th")]
        
        print(f"Headers found: {headers}")
        
        # Get all rows from tbody
        tbody = table.find_element(By.TAG_NAME, "tbody")
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        
        # Extract data from each row
        data = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            row_data = []
            
            for cell in cells:
                # Get the text content, stripping whitespace
                cell_text = cell.text.strip()
                row_data.append(cell_text)
            
            if row_data:  # Only add non-empty rows
                data.append(row_data)
        
        print(f"Found {len(data)} rows of data")
        # Create DataFrame
        df = pd.DataFrame(data)
        if len(df.columns) == len(headers):
            df.columns = headers
        else:
            print("Warning: Number of columns in data does not match number of headers. Headers will not be set.")

        # Save to Excel file
        df.to_excel(output_filename, index=False)
        print(f"Data saved to {output_filename}")
        
        # Display first few rows
        print("\nFirst 5 rows of data:")
        print(df.head())
        
        return df
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
        
    finally:
        driver.quit()

# Usage
if __name__ == "__main__":
    # Get today's date in MM/DD/YY format
    today = datetime.today().strftime('%m/%d/%y')

# Insert it into the URL
    url = f"https://www.equibase.com/premium/eqpInTodayAction.cfm?DATE={today}&TYPE=H&VALUE=ALL"
    
    # Scrape the data and save to Excel
    df = scrape_equibase_table(url, "equibase_today_horses_data.xlsx")
    
    if df is not None:
        print(f"\nScraping completed successfully!")
        print(f"Total rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
    else:
        print("Scraping failed!")