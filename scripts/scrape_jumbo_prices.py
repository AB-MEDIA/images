#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape retail prices from Jumbo.cl for products in product_challenge table
Similar to scrape_jumbo_images.py but extracts prices instead
"""
import json
import sys
import csv
from pathlib import Path
import time
import requests
from urllib.parse import quote
import re

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("Installing selenium...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium", "webdriver-manager", "--quiet"])
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

# Fix encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Get to database directory: scripts -> images -> database
SCRIPT_DIR = Path(__file__).resolve().parent  # database/images/scripts
IMAGES_DIR = SCRIPT_DIR.parent  # database/images
DATABASE_DIR = IMAGES_DIR.parent  # database
CSV_DIR = DATABASE_DIR / 'csv'

def setup_driver():
    """Setup Chrome driver for Selenium"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"  Warning: Could not use webdriver-manager: {e}")
        driver = webdriver.Chrome(options=options)
    
    return driver

def extract_price_from_text(text):
    """Extract price number from text (handles CLP format like $5.990 or 5990)"""
    if not text:
        return None
    
    # Remove currency symbols and spaces
    text = text.replace('$', '').replace('CLP', '').replace('clp', '').strip()
    # Remove dots (Chilean format: $5.990 = 5990)
    text = text.replace('.', '')
    # Remove commas if any
    text = text.replace(',', '')
    
    # Extract numbers
    numbers = re.findall(r'\d+', text)
    if numbers:
        # Take the largest number found (in case of multiple matches)
        return max([int(n) for n in numbers])
    return None

def search_jumbo_price(product_name, sku, driver):
    """Search Jumbo.cl using Selenium and return price"""
    base_url = "https://www.jumbo.cl/busqueda"
    # Try searching by SKU first, then by product name
    search_queries = [sku] if sku else []
    search_queries.append(product_name)
    
    for search_query in search_queries:
        if not search_query or not search_query.strip():
            continue
            
        url = f"{base_url}?ft={quote(search_query)}"
        
        print(f"  Searching: {url}")
        
        try:
            driver.get(url)
            time.sleep(3)  # Wait for JavaScript to load
            
            # Try multiple selectors for price
            price_selectors = [
                # Common price selectors on Jumbo.cl
                "span[class*='price']",
                "div[class*='price']",
                "p[class*='price']",
                ".vtex-product-price-1-x-sellingPrice",
                ".vtex-product-price-1-x-listPrice",
                "[data-testid*='price']",
                # Look for text containing $ or CLP
                "//*[contains(text(), '$')]",
                "//*[contains(text(), 'CLP')]",
            ]
            
            price = None
            
            # Try CSS selectors first
            for selector in price_selectors[:6]:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and ('$' in text or 'CLP' in text or any(c.isdigit() for c in text)):
                            extracted = extract_price_from_text(text)
                            if extracted and extracted > 100:  # Reasonable minimum price
                                price = extracted
                                print(f"    Found price: ${price:,} CLP (selector: {selector})")
                                break
                    if price:
                        break
                except:
                    continue
            
            # Try XPath if CSS didn't work
            if not price:
                try:
                    xpath_elements = driver.find_elements(By.XPATH, price_selectors[6])
                    for elem in xpath_elements:
                        text = elem.text.strip()
                        if text:
                            extracted = extract_price_from_text(text)
                            if extracted and extracted > 100:
                                price = extracted
                                print(f"    Found price: ${price:,} CLP (XPath)")
                                break
                except:
                    pass
            
            # Fallback: search page source for price patterns
            if not price:
                page_source = driver.page_source
                # Look for patterns like $5.990 or 5990 CLP
                price_patterns = [
                    r'\$\s*(\d{1,3}(?:\.\d{3})*)',  # $5.990 format
                    r'(\d{1,3}(?:\.\d{3})*)\s*CLP',  # 5990 CLP format
                    r'price["\']?\s*:\s*["\']?(\d+)',  # JSON price
                ]
                
                for pattern in price_patterns:
                    matches = re.findall(pattern, page_source)
                    if matches:
                        # Take first reasonable match
                        for match in matches:
                            extracted = extract_price_from_text(match)
                            if extracted and extracted > 100:
                                price = extracted
                                print(f"    Found price: ${price:,} CLP (pattern match)")
                                break
                        if price:
                            break
            
            if price:
                return price
            
        except Exception as e:
            print(f"    Error searching: {e}")
            continue
    
    return None

def build_search_query_from_product_name(name):
    """Build search query from product name (similar to image scraper logic)"""
    if not name:
        return None
    
    name_lower = name.lower()
    
    # Build search query from key product terms
    # For L'Oreal products, search by brand + key product name
    if "elvive" in name_lower:
        if "hialuronico" in name_lower or "micelar" in name_lower:
            return "elvive hialuronico shampoo"
        elif "color vive" in name_lower:
            if "shampoo" in name_lower:
                return "elvive color vive shampoo violeta"
            elif "acondicionador" in name_lower:
                return "elvive color vive acondicionador violeta"
        elif "oleo extraordinario" in name_lower or "óleo extraordinario" in name_lower:
            if "shampoo" in name_lower:
                return "elvive oleo extraordinario shampoo"
            else:
                return "elvive oleo extraordinario tratamiento"
    elif "infallible" in name_lower or "infaillible" in name_lower:
        if "matte resistance" in name_lower:
            if "625" in name_lower or "summer fling" in name_lower:
                return "infallible matte resistance 625"
            elif "fairytale" in name_lower:
                return "infallible matte resistance fairytale"
        else:
            return "infallible matte"
    elif "telescopic" in name_lower:
        return "loreal telescopic lift mascara"
    elif "glycolic" in name_lower or "gloss" in name_lower or "acidifier" in name_lower:
        return "elvive glycolic gloss"
    elif "revitalift" in name_lower or ("crema" in name_lower and "noche" in name_lower):
        return "loreal revitalift crema noche"
    else:
        # Fallback: use first few meaningful words
        words = [w for w in name_lower.split() if len(w) > 3][:4]
        return ' '.join(words) if words else name_lower

# Load product_challenge and product tables
print("=" * 80)
print("LOADING PRODUCT CHALLENGE AND PRODUCT TABLES")
print("=" * 80)
print()

product_challenge_file = CSV_DIR / 'product_challenge.csv'
product_file = CSV_DIR / 'product.csv'

if not product_challenge_file.exists():
    print(f"[!] Error: {product_challenge_file} not found")
    sys.exit(1)

if not product_file.exists():
    print(f"[!] Error: {product_file} not found")
    sys.exit(1)

# Read product_challenge table
product_challenges = []
with open(product_challenge_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    product_challenges = list(reader)

print(f"Loaded {len(product_challenges)} product_challenge records")

# Read product table and create lookup by _id
products_lookup = {}
with open(product_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        products_lookup[row['_id']] = row

print(f"Loaded {len(products_lookup)} products for lookup")
print()

# Setup Selenium driver
print("Setting up browser...")
try:
    driver = setup_driver()
    print("  [+] Browser ready\n")
except Exception as e:
    print(f"  [!] Failed to setup browser: {e}")
    sys.exit(1)

# Process each product_challenge
updated_count = 0
failed_count = 0
skipped_count = 0

for i, pc in enumerate(product_challenges, 1):
    print(f"\n{'='*80}")
    print(f"PRODUCT CHALLENGE {i}/{len(product_challenges)}")
    print(f"{'='*80}")
    print(f"ID: {pc['_id']}")
    
    # Check if already has price
    current_price = pc.get('pvp_number', '').strip()
    if current_price and current_price.isdigit():
        print(f"  [SKIP] Already has price: ${int(current_price):,} CLP")
        skipped_count += 1
        continue
    
    # Get product FK
    product_id = pc.get('product_custom_product', '').strip()
    if not product_id:
        print(f"  [!] No product FK found")
        failed_count += 1
        continue
    
    # Lookup product
    product = products_lookup.get(product_id)
    if not product:
        print(f"  [!] Product not found: {product_id}")
        failed_count += 1
        continue
    
    # Get SKU and product name
    sku = product.get('sku_text', '').strip()
    product_name = product.get('name1_text', '').strip()
    
    print(f"  Product: {product_name}")
    print(f"  SKU: {sku}")
    
    if not sku and not product_name:
        print(f"  [!] No SKU or product name available")
        failed_count += 1
        continue
    
    # Build search query
    search_query = build_search_query_from_product_name(product_name) if product_name else sku
    
    # Search for price
    price = search_jumbo_price(search_query, sku, driver)
    
    if price:
        # Update the record
        pc['pvp_number'] = str(price)
        updated_count += 1
        print(f"  [+] Price found: ${price:,} CLP")
    else:
        print(f"  [!] Price not found")
        failed_count += 1
        print(f"      Try searching manually: https://www.jumbo.cl/busqueda?ft={quote(search_query)}")
    
    time.sleep(2)  # Pause between searches

# Close browser
driver.quit()

print("\n" + "=" * 80)
print("SCRAPING COMPLETE")
print("=" * 80)
print(f"\nUpdated: {updated_count}")
print(f"Failed: {failed_count}")
print(f"Skipped (already had price): {skipped_count}")

# Save updated product_challenge CSV
if updated_count > 0:
    print(f"\nSaving updated product_challenge.csv...")
    
    # Read original headers
    with open(product_challenge_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
    
    # Write updated data
    with open(product_challenge_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(product_challenges)
    
    print(f"[+] Saved updated product_challenge.csv")
    print(f"\nNext: Push changes to Bubble using:")
    print(f"  cd database/sync_process")
    print(f"  python bubble_sync.py from_local product_challenge")
else:
    print(f"\nNo prices were updated. CSV file not modified.")

