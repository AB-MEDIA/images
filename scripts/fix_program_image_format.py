#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix image field format in program.csv
Image fields should be comma-separated URLs, not nested arrays
"""
import csv
import re
import sys
from pathlib import Path

# Fix encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Get to database directory
SCRIPT_DIR = Path(__file__).resolve().parent
DATABASE_DIR = SCRIPT_DIR.parent.parent
CSV_DIR = DATABASE_DIR / 'csv'

def clean_image_urls(value):
    """Extract clean URLs from nested format and return comma-separated format"""
    if not value or not value.strip():
        return ''
    
    # Extract all URLs starting with //
    urls = re.findall(r'//[^\'"\s\[\],]+', str(value))
    
    # Remove duplicates while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        # Clean up any trailing escape characters
        url = url.rstrip('\\').rstrip('"').rstrip("'").rstrip(']').rstrip(')')
        if url and url not in seen:
            seen.add(url)
            unique_urls.append(url)
    
    return ','.join(unique_urls)

# Read CSV
program_file = CSV_DIR / 'program.csv'

print("=" * 80)
print("FIXING IMAGE FIELD FORMAT IN PROGRAM.CSV")
print("=" * 80)
print()

with open(program_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = list(reader.fieldnames)
    rows = list(reader)

print(f"Loaded {len(rows)} records")

# Clean image fields
for row in rows:
    if 'banners_list_image' in row:
        old_val = row['banners_list_image']
        new_val = clean_image_urls(old_val)
        row['banners_list_image'] = new_val
        if old_val != new_val:
            print(f"  Fixed banners_list_image: {len(old_val)} -> {len(new_val)} chars")
    
    if 'posters_square_list_image' in row:
        old_val = row['posters_square_list_image']
        new_val = clean_image_urls(old_val)
        row['posters_square_list_image'] = new_val
        if old_val != new_val:
            print(f"  Fixed posters_square_list_image: {len(old_val)} -> {len(new_val)} chars")

# Write back
with open(program_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"\n[+] Saved updated program.csv")
print("\nVerification:")
for i, row in enumerate(rows, 1):
    if row.get('name_text'):
        banners = row.get('banners_list_image', '')
        posters = row.get('posters_square_list_image', '')
        print(f"\n{row.get('name_text', 'N/A')}:")
        if banners:
            urls = banners.split(',')
            print(f"  Banners: {len(urls)} URL(s) - Format: comma-separated")
            print(f"    Example: {urls[0][:80]}...")
        else:
            print(f"  Banners: (empty)")
        if posters:
            urls = posters.split(',')
            print(f"  Posters: {len(urls)} URL(s) - Format: comma-separated")
        else:
            print(f"  Posters: (empty)")

