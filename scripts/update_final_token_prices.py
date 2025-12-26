#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update product_challenge CSV with final token price values
"""
import csv
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

# Final values provided by user
final_values = [
    {
        '_id': '1765145428310x333400327492867400',
        'token_price_number': '6',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145429762x164234135966944350',
        'token_price_number': '7',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145430800x127220685623587340',
        'token_price_number': '2',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145431963x751118130443184600',
        'token_price_number': '3',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145433052x654690137555272700',
        'token_price_number': '4',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145434224x100938318907304320',
        'token_price_number': '7',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145435476x138923755421354930',
        'token_price_number': '4',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145436520x425172236358683650',
        'token_price_number': '7',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145437540x340180091913216800',
        'token_price_number': '7',
        'price_currency_option_currency_type': 'token'
    },
    {
        '_id': '1765145438838x831403677751094700',
        'token_price_number': '7',
        'price_currency_option_currency_type': 'token'
    },
]

# Create lookup by _id
final_lookup = {v['_id']: v for v in final_values}

# Load and update CSV
product_challenge_file = CSV_DIR / 'product_challenge.csv'

print("=" * 80)
print("UPDATING PRODUCT_CHALLENGE WITH FINAL TOKEN PRICES")
print("=" * 80)
print()

# Read current CSV
with open(product_challenge_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    records = list(reader)

print(f"Loaded {len(records)} records")

# Update records
updated_count = 0
for record in records:
    record_id = record.get('_id', '').strip()
    if record_id in final_lookup:
        final_data = final_lookup[record_id]
        record['token_price_number'] = final_data['token_price_number']
        record['price_currency_option_currency_type'] = final_data['price_currency_option_currency_type']
        updated_count += 1
        print(f"  Updated: {record_id[:30]}... -> {final_data['token_price_number']} tokens")

print(f"\nUpdated {updated_count} records")

# Save updated CSV
print(f"\nSaving updated product_challenge.csv...")
with open(product_challenge_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"[+] Saved updated product_challenge.csv")
print(f"\nNext: Push changes to Bubble using:")
print(f"  cd database/sync_process")
print(f"  python bubble_sync.py from_local product_challenge")

