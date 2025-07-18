from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
from urllib.parse import urlparse, parse_qs
import os
import csv
import time
import pandas as pd
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
    options.add_argument("--disable-webgl")  # Disable WebGL
    options.add_argument("--disable-gpu")  # Ensure GPU acceleration is off
    driver = uc.Chrome(options=options)
    return driver




def download_pdfs(data_list):
    driver = get_driver()

    csv_file = 'pdf_data.csv'
    existing_urls = set()

    # Load existing pdf_url values if CSV exists
    if os.path.exists(csv_file):
        df_existing = pd.read_csv(csv_file)
        if 'pdf_url' in df_existing.columns:
            existing_urls = set(df_existing['pdf_url'].dropna().tolist())

    # Ensure consistent field order
    fieldnames = ['source_url', 'track_name', 'track_link', 'date', 'pdf_url']

    for item in data_list:
        try:
            driver.get(item['track_link'])

            full_card_link = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//h3/a[b[text()="View the Full Card Here"]]'))
            )
            full_card_href = full_card_link.get_attribute('href')

            if full_card_href.startswith("/"):
                full_card_href = "https://www.equibase.com" + full_card_href

            print(f"➡️ Going to Full Card Page: {full_card_href}")
            driver.get(full_card_href)

            pdf_object = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'object'))
            )
            pdf_url = pdf_object.get_attribute("data")

            if pdf_url.startswith("/"):
                pdf_url = "https://www.equibase.com" + pdf_url

            item['pdf_url'] = pdf_url

            if pdf_url not in existing_urls:
                # Save immediately to CSV
                write_header = not os.path.exists(csv_file) or os.stat(csv_file).st_size == 0
                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    if write_header:
                        writer.writeheader()
                    writer.writerow(item)

                existing_urls.add(pdf_url)
                print(f"✅ Saved to CSV: {pdf_url}")
            else:
                print(f"🔁 Duplicate skipped: {pdf_url}")

        except Exception as e:
            print(f"⚠️ Error processing {item['track_link']}: {e}")

    driver.quit()

def extract_date_from_url(url):
    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    day = query.get('da', [''])[0]
    month = query.get('mo', [''])[0]
    year = query.get('yr', [''])[0]
    return f"{day.zfill(2)}-{month.zfill(2)}-{year}"


def scrape_equibase_calendar(month, year, base_url="https://www.equibase.com/premium/eqbRaceChartCalendar.cfm"):
    """
    Scrape Equibase calendar for a specific month and year
    
    Args:
        month (int): Month number (1-12)
        year (int): Year (e.g., 2025)
        base_url (str): Base URL for the calendar
    
    Returns:
        list: List of all URLs from elements with class "dkbluesm"
    """
    
    links_list = []
    driver=get_driver()
    try:
        # Navigate to the page
        driver.get(base_url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "month"))
        )
        
        # Select the month
        month_select = Select(driver.find_element(By.NAME, "month"))
        month_select.select_by_value(str(month))
        
        # Select the year
        year_select = Select(driver.find_element(By.NAME, "YEAR"))
        year_select.select_by_value(str(year))
        
        # Click the search button
        search_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Search']")
        search_button.click()
        
        # Wait for the results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dkbluesm"))
        )
        
        # Find all links with class "dkbluesm"
        calendar_links = driver.find_elements(By.CLASS_NAME, "dkbluesm")
        
        # Extract href attributes and filter by month parameter
        for link in calendar_links:
            href = link.get_attribute("href")
            if href and f"mo={month}" in href:
                # Convert relative URLs to absolute URLs if needed
                if href.startswith("eqpVchartBuy.cfm"):
                    full_url = "https://www.equibase.com/premium/" + href
                else:
                    full_url = href
                links_list.append(full_url)
        
        print(f"Found {len(links_list)} links for month {month} in year {year}")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
    finally:
        driver.quit()
    
    return links_list


def scrape_tracks(url_list):
    all_tracks = []
    driver=get_driver()
    for url in url_list:
        print(f"Visiting: {url}")
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "dkbluesm"))
            )
            time.sleep(1)  # small wait to ensure rendering

            links = driver.find_elements(By.CLASS_NAME, "dkbluesm")
            for link in links:
                track_name = link.text.strip()
                track_href = link.get_attribute("href")
                date = extract_date_from_url(url)

                all_tracks.append({
                    "source_url": url,
                    "track_name": track_name,
                    "track_link": track_href,
                    "date": date
                })
        except Exception as e:
            print(f"Failed on {url} with error: {e}")

    driver.quit()
    return all_tracks

month = 7  
year = 2025
    
print(f"Scraping calendar for {month}/{year}...")
links = scrape_equibase_calendar(month, year)
    
results = scrape_tracks(links)
download_pdfs(results)


