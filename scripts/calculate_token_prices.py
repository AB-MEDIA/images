#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calculate token prices for product_challenge records
- Token prices are a linear transformation of retail price (pvp_number)
- Token prices are full integers
- RULE: sum(token_price * stock_initial) = 11,000
- Update price_currency to 'token'
"""
import csv
import sys
from pathlib import Path

# Fix encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Get to database directory: scripts -> images -> database
SCRIPT_DIR = Path(__file__).resolve().parent  # database/images/scripts
IMAGES_DIR = SCRIPT_DIR.parent  # database/images
DATABASE_DIR = IMAGES_DIR.parent  # database
CSV_DIR = DATABASE_DIR / 'csv'

TARGET_SUM = 11000  # sum(token_price * stock_initial) = 11,000

def calculate_token_prices(product_challenges):
    """
    Calculate token prices based on retail price
    
    Strategy:
    1. Calculate proportional token prices based on retail price (linear transformation)
    2. Scale so that sum(token_price * stock_initial) = TARGET_SUM
    3. Round to integers
    4. Adjust rounding errors to ensure exact sum
    """
    # Filter records with valid retail price and stock_initial
    valid_records = []
    for pc in product_challenges:
        pvp = pc.get('pvp_number', '').strip()
        stock_initial = pc.get('nr_provogrammers_number', '').strip()
        
        if pvp and pvp.isdigit() and stock_initial and stock_initial.isdigit():
            pvp_val = float(pvp)
            stock_val = float(stock_initial)
            if pvp_val > 0 and stock_val > 0:
                valid_records.append({
                    'record': pc,
                    'pvp': pvp_val,
                    'stock_initial': stock_val,
                })
    
    if not valid_records:
        print("[!] No valid records with retail price and stock_initial found")
        return False
    
    print(f"\nFound {len(valid_records)} valid records")
    print(f"Target: sum(token_price * stock_initial) = {TARGET_SUM:,}")
    
    # Calculate total retail price * stock for normalization
    total_pvp_stock = sum(r['pvp'] * r['stock_initial'] for r in valid_records)
    
    if total_pvp_stock == 0:
        print("[!] Total pvp * stock is zero, cannot calculate token prices")
        return False
    
    print(f"Total (retail_price * stock_initial): {total_pvp_stock:,.2f}")
    print()
    
    # Calculate proportional token prices (linear transformation)
    # We want: sum(token_price * stock_initial) = TARGET_SUM
    # If we use proportional allocation: token_price = k * retail_price
    # Then: sum(k * retail_price * stock_initial) = TARGET_SUM
    # So: k = TARGET_SUM / sum(retail_price * stock_initial)
    
    k = TARGET_SUM / total_pvp_stock
    
    print(f"Scaling factor (k): {k:.6f}")
    print(f"This means: token_price ≈ {k:.4f} * retail_price")
    print()
    
    token_allocations = []
    total_weighted_sum = 0
    
    for r in valid_records:
        # Calculate token price as linear transformation of retail price
        token_price_float = r['pvp'] * k
        token_price_int = int(round(token_price_float))
        
        # Ensure minimum of 1 token
        if token_price_int < 1:
            token_price_int = 1
        
        weighted_value = token_price_int * r['stock_initial']
        token_allocations.append({
            'record': r['record'],
            'token_price_float': token_price_float,
            'token_price_int': token_price_int,
            'stock_initial': r['stock_initial'],
            'weighted_value': weighted_value
        })
        total_weighted_sum += weighted_value
    
    # Adjust for rounding errors to ensure exact sum
    # Strategy: Calculate target weighted value for each product proportionally
    # Then solve for token_price = target_weighted / stock_initial
    # Round and adjust systematically
    
    # Calculate target weighted value for each product (proportional to pvp * stock)
    total_pvp_stock = sum(r['pvp'] * r['stock_initial'] for r in valid_records)
    for alloc in token_allocations:
        pvp = alloc['record'].get('pvp_number', '').strip()
        pvp_val = float(pvp) if pvp else 0
        stock = alloc['stock_initial']
        target_weighted = (pvp_val * stock / total_pvp_stock) * TARGET_SUM
        alloc['target_weighted'] = target_weighted
        alloc['target_token_price'] = target_weighted / stock if stock > 0 else 0
    
    # Round target token prices to integers
    for alloc in token_allocations:
        alloc['token_price_int'] = max(1, int(round(alloc['target_token_price'])))
        alloc['weighted_value'] = alloc['token_price_int'] * alloc['stock_initial']
    
    # Calculate difference and adjust systematically
    current_sum = sum(a['weighted_value'] for a in token_allocations)
    difference = TARGET_SUM - current_sum
    
    if difference != 0:
        print(f"Initial weighted sum: {current_sum:,}, target: {TARGET_SUM:,}, difference: {difference}")
        
        # Sort by how close we are to target (fractional part)
        token_allocations.sort(
            key=lambda x: abs(x['target_token_price'] - x['token_price_int']),
            reverse=True
        )
        
        # Adjust systematically
        if difference > 0:
            # Need to increase: add tokens to products with largest rounding error
            for alloc in token_allocations:
                if difference > 0:
                    alloc['token_price_int'] += 1
                    alloc['weighted_value'] = alloc['token_price_int'] * alloc['stock_initial']
                    difference -= alloc['stock_initial']
        else:
            # Need to decrease: remove tokens from products with largest rounding error
            for alloc in token_allocations:
                if difference < 0 and alloc['token_price_int'] > 1:
                    alloc['token_price_int'] -= 1
                    alloc['weighted_value'] = alloc['token_price_int'] * alloc['stock_initial']
                    difference += alloc['stock_initial']
        
        # Fine-tune if still not exact
        current_sum = sum(a['weighted_value'] for a in token_allocations)
        remaining_diff = TARGET_SUM - current_sum
        
        if abs(remaining_diff) > 0:
            # Sort by stock size (smallest first for fine adjustments)
            token_allocations.sort(key=lambda x: x['stock_initial'])
            
            # Try to find exact match by adjusting smallest stocks
            for alloc in token_allocations:
                stock = alloc['stock_initial']
                if remaining_diff > 0:
                    # Increase by 1 token
                    alloc['token_price_int'] += 1
                    alloc['weighted_value'] = alloc['token_price_int'] * stock
                    remaining_diff -= stock
                elif remaining_diff < 0 and alloc['token_price_int'] > 1:
                    # Decrease by 1 token
                    alloc['token_price_int'] -= 1
                    alloc['weighted_value'] = alloc['token_price_int'] * stock
                    remaining_diff += stock
                
                if abs(remaining_diff) == 0:
                    break
    
    # Verify sum
    final_sum = sum(a['weighted_value'] for a in token_allocations)
    print(f"Final weighted sum: {final_sum:,} (target: {TARGET_SUM:,})")
    
    if final_sum != TARGET_SUM:
        print(f"[!] WARNING: Sum mismatch! Difference: {final_sum - TARGET_SUM}")
        print(f"    This may be due to integer rounding constraints.")
    
    # Update records
    print("\n" + "=" * 80)
    print("TOKEN PRICE ALLOCATION")
    print("=" * 80)
    
    total_stock = 0
    for alloc in token_allocations:
        record = alloc['record']
        tokens = alloc['token_price_int']
        pvp = float(record.get('pvp_number', '').strip() or 0)
        stock_initial = alloc['stock_initial']
        weighted = alloc['weighted_value']
        
        record['token_price_number'] = str(tokens)
        record['price_currency_option_currency_type'] = 'token'
        
        total_stock += stock_initial
        
        print(f"  Product ID: {record['_id'][:30]}...")
        print(f"    Retail Price: ${int(pvp):,} CLP")
        print(f"    Stock Initial: {int(stock_initial)}")
        print(f"    Token Price: {tokens} tokens")
        print(f"    Weighted Value: {weighted} (tokens × stock)")
        print()
    
    avg_price = final_sum / total_stock if total_stock > 0 else 0
    print(f"Total stock: {int(total_stock)}")
    print(f"Average token price: {avg_price:.2f} tokens")
    print(f"Total weighted sum: {final_sum:,}")
    
    return True

# Load product_challenge table
print("=" * 80)
print("CALCULATING TOKEN PRICES FOR PRODUCT_CHALLENGE")
print("=" * 80)
print()

product_challenge_file = CSV_DIR / 'product_challenge.csv'

if not product_challenge_file.exists():
    print(f"[!] Error: {product_challenge_file} not found")
    sys.exit(1)

# Read product_challenge table
product_challenges = []
with open(product_challenge_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    product_challenges = list(reader)

print(f"Loaded {len(product_challenges)} product_challenge records")

# Calculate token prices
if calculate_token_prices(product_challenges):
    # Save updated CSV
    print("\nSaving updated product_challenge.csv...")
    
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
    print("\n[!] Failed to calculate token prices")
