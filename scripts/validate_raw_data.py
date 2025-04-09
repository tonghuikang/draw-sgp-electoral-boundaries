#!/usr/bin/env python3

import json

# Load the raw data with all electoral divisions and polling districts
with open('raw_data/ge2025_electoral_divisions_and_polling_districts.json') as f:
    raw = json.load(f)

# Extract all polling districts from raw data
raw_districts = [pd for const in raw for pd in const['polling_districts']]
print(f'Total raw districts: {len(raw_districts)}')
print(f'Unique raw districts: {len(set(raw_districts))}')

# Load processed GeoJSON with elector size
with open('processed_data/ge2025_polling_districts_with_elector_size.geojson') as f:
    processed = json.load(f)

# Extract polling district IDs from processed data
processed_districts = [feature['properties']['name'] for feature in processed['features']]
print(f'Total processed districts: {len(processed_districts)}')
print(f'Unique processed districts: {len(set(processed_districts))}')

# Find missing districts
missing = set(raw_districts) - set(processed_districts)
print(f'Missing districts count: {len(missing)}')
print('Missing districts:')
print(sorted(missing))

# Find electoral divisions with missing districts
if missing:
    print('\nElectoral divisions with missing districts:')
    for const in raw:
        const_missing = set(const['polling_districts']) & missing
        if const_missing:
            print(f"{const['constituency_name']}: {sorted(const_missing)}")

# Check for duplicate polling districts in raw data
print("\nDuplicate polling districts in raw data:")
raw_counts = {}
for district in raw_districts:
    raw_counts[district] = raw_counts.get(district, 0) + 1
duplicates_raw = {d: count for d, count in raw_counts.items() if count > 1}
if duplicates_raw:
    for district, count in sorted(duplicates_raw.items()):
        print(f"{district}: appears {count} times")
        # Show which constituencies have this duplicate
        for const in raw:
            if district in const['polling_districts']:
                print(f"  - Found in {const['constituency_name']}")
else:
    print("None")

# Check for duplicate polling districts in processed data
print("\nDuplicate polling districts in processed data:")
processed_counts = {}
for district in processed_districts:
    processed_counts[district] = processed_counts.get(district, 0) + 1
duplicates_processed = {d: count for d, count in processed_counts.items() if count > 1}
if duplicates_processed:
    for district, count in sorted(duplicates_processed.items()):
        print(f"{district}: appears {count} times")
else:
    print("None")