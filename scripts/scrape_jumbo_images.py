#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape product images from Jumbo.cl using Selenium (handles JavaScript)
"""
import json
import sys
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

BASE_DIR = Path(__file__).parent.parent.parent  # scripts -> images -> database
IMAGES_DIR = BASE_DIR / 'images'
CSV_DIR = BASE_DIR / 'csv'

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
    except:
        driver = webdriver.Chrome(options=options)
    
    return driver

def search_jumbo_selenium(product_name, driver, search_keywords=None):
    """Search Jumbo.cl using Selenium and return matching image URLs"""
    base_url = "https://www.jumbo.cl/busqueda"
    url = f"{base_url}?ft={quote(product_name)}"
    
    print(f"Loading: {url}")
    
    try:
        driver.get(url)
        time.sleep(3)  # Wait for JavaScript to load
        
        image_urls = []
        img_elements = driver.find_elements(By.TAG_NAME, 'img')
        
        for img in img_elements:
            src = img.get_attribute('src') or img.get_attribute('data-src')
            if src and 'jumbocl.vteximg.com.br' in src:
                if 'favicon' not in src.lower() and 'ids/' in src:
                    # Extract filename from URL to match product
                    filename_match = re.search(r'/([^/]+\.(?:jpg|jpeg|png|webp))', src)
                    if filename_match:
                        filename = filename_match.group(1).lower()
                        # Match based on keywords in filename
                        if search_keywords:
                            if any(kw.lower() in filename for kw in search_keywords if len(kw) > 3):
                                image_urls.append(src)
                        else:
                            image_urls.append(src)
        
        return list(set(image_urls))[:10]  # Remove duplicates, return first 10
        
    except Exception as e:
        print(f"  Error: {e}")
        return []

def download_image(url, save_path):
    """Download an image from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return True, str(save_path)
    except Exception as e:
        return False, str(e)

# Load products needing images
products_file = BASE_DIR / 'images' / 'redemption_products_needing_images.json'
with open(products_file, 'r', encoding='utf-8') as f:
    products = json.load(f)

print("=" * 80)
print("SCRAPING PRODUCT IMAGES FROM JUMBO.CL (USING SELENIUM)")
print("=" * 80)
print()

# Setup Selenium driver once
print("Setting up browser...")
try:
    driver = setup_driver()
    print("  [+] Browser ready\n")
except Exception as e:
    print(f"  [!] Failed to setup browser: {e}")
    sys.exit(1)

# Process each product
downloaded_data = []  # Store downloaded URLs for each product

for i, product in enumerate(products, 1):
    print(f"\n{'='*80}")
    print(f"PRODUCT {i}/{len(products)}: {product['name']}")
    print(f"{'='*80}")
    print(f"SKU: {product['sku']}")
    print(f"Current: {product['image_count']} image(s)")
    
    # Create better search query - extract key identifying words
    name = product['name'].lower()
    
    # Build search query from key product terms
    # For L'Oreal products, search by brand + key product name
    if "elvive" in name:
        if "hialuronico" in name or "micelar" in name:
            search_query = "elvive hialuronico shampoo"
        elif "color vive" in name:
            if "shampoo" in name:
                search_query = "elvive color vive shampoo violeta"
            elif "acondicionador" in name:
                search_query = "elvive color vive acondicionador violeta"
        elif "oleo extraordinario" in name or "óleo extraordinario" in name:
            if "shampoo" in name:
                search_query = "elvive oleo extraordinario shampoo"
            else:
                search_query = "elvive oleo extraordinario tratamiento"
    elif "infallible" in name or "infaillible" in name:
        if "matte resistance" in name:
            if "625" in name or "summer fling" in name:
                search_query = "infallible matte resistance 625"
            elif "fairytale" in name:
                search_query = "infallible matte resistance fairytale"
        else:
            search_query = "infallible matte"
    elif "telescopic" in name:
        search_query = "loreal telescopic lift mascara"
    elif "glycolic" in name or "gloss" in name or "acidifier" in name:
        search_query = "elvive glycolic gloss"
    elif "revitalift" in name or "crema" in name and "noche" in name:
        search_query = "loreal revitalift crema noche"
    else:
        # Fallback: use first few meaningful words
        words = [w for w in name.split() if len(w) > 3][:4]
        search_query = ' '.join(words)
    
    print(f"\nSearching for: {search_query}")
    
    # Extract keywords for matching
    keywords = search_query.split()
    
    # Search Jumbo with Selenium
    image_urls = search_jumbo_selenium(search_query, driver, search_keywords=keywords)
    
    if not image_urls:
        print("  [!] No images found in search results")
        print(f"      Try searching manually: https://www.jumbo.cl/busqueda?ft={quote(search_query)}")
        continue
    
    print(f"\n  Found {len(image_urls)} potential images")
    
    # Download 3 images for each product (always)
    needed = 3
    downloaded_urls = []
    github_base = "https://github.com/AB-MEDIA/images/raw/main/"
    
    for idx, img_url in enumerate(image_urls[:needed], 1):
        # Generate filename
        ext = '.jpg'  # Default
        if '.png' in img_url.lower():
            ext = '.png'
        elif '.webp' in img_url.lower():
            ext = '.webp'
        
        # Always name sequentially: sku-image-1.jpg, sku-image-2.jpg, etc.
        filename = f"{product['sku']}-jumbo-{idx}{ext}"
        
        save_path = IMAGES_DIR / filename
        
        print(f"\n  Downloading image {idx}/{needed}...")
        print(f"    URL: {img_url[:80]}...")
        
        success, result = download_image(img_url, save_path)
        if success:
            github_url = github_base + filename
            downloaded_urls.append(github_url)
            print(f"    [+] Saved: {filename}")
        else:
            print(f"    [!] Failed: {result}")
        
        time.sleep(1)  # Be nice to the server
    
    if downloaded_urls:
        print(f"\n  [+] Successfully downloaded {len(downloaded_urls)} image(s)")
        # Store for later update
        downloaded_data.append({
            'product_id': product['product_id'],
            'current_images': product['current_images'],
            'new_urls': downloaded_urls
        })
    else:
        print(f"\n  [!] Failed to download any images")
    
    time.sleep(2)  # Pause between products

# Close browser
driver.quit()

print("\n" + "=" * 80)
print("SCRAPING COMPLETE")
print("=" * 80)
print(f"\nDownloaded images for {len(downloaded_data)} products")

# Save downloaded data for update script
download_info_file = BASE_DIR / 'images' / 'downloaded_images_info.json'
with open(download_info_file, 'w', encoding='utf-8') as f:
    json.dump(downloaded_data, f, indent=2, ensure_ascii=False)
print(f"Saved download info to: {download_info_file}")

print("\nNext: Update products with downloaded images and push to Bubble")

