#!/usr/bin/env python3

import json

# Load the raw data with all polling districts and elector size
with open('raw_data/ge2025_polling_districts_and_elector_size.json') as f:
    raw = json.load(f)

# Extract all polling districts from raw data
raw_districts = []
for item in raw:
    raw_districts.extend(item['polling_districts'])
print(f'Total raw districts: {len(raw_districts)}')
print(f'Unique raw districts: {len(set(raw_districts))}')

# Load processed GeoJSON with elector size
with open('processed_data/ge2025_polling_districts_with_elector_size.geojson') as f:
    processed = json.load(f)

# Extract polling district IDs from processed data
processed_districts = [feature['properties']['name'] for feature in processed['features']]
print(f'Total processed districts: {len(processed_districts)}')
print(f'Unique processed districts: {len(set(processed_districts))}')

# Find districts in raw data but missing from processed data
missing_from_processed = set(raw_districts) - set(processed_districts)
print(f'Districts in raw data but missing from processed data count: {len(missing_from_processed)}')
print('Districts in raw data but missing from processed data:')
print(sorted(missing_from_processed))

# Find districts in processed data but missing from raw data
missing_from_raw = set(processed_districts) - set(raw_districts)
print(f'Districts in processed data but missing from raw data count: {len(missing_from_raw)}')
print('Districts in processed data but missing from raw data:')
print(sorted(missing_from_raw))

# Find polling districts that are in ge2025_polling_districts_and_elector_size.json
# but missing from the processed ge2025_polling_districts_with_elector_size.geojson
if missing_from_processed:
    print('\nPolling districts found in ge2025_polling_districts_and_elector_size.json')
    print('but missing from ge2025_polling_districts_with_elector_size.geojson:')
    print(sorted(missing_from_processed))

# Report on polling districts in ge2025_polling_districts_with_elector_size.geojson 
# but not found in ge2025_polling_districts_and_elector_size.json
if missing_from_raw:
    print('\nPolling districts found in ge2025_polling_districts_with_elector_size.geojson')
    print('but not present in ge2025_polling_districts_and_elector_size.json:')
    print(sorted(missing_from_raw))

# Check for duplicate polling districts in ge2025_polling_districts_and_elector_size.json
print("\nDuplicate polling districts in ge2025_polling_districts_and_elector_size.json:")
raw_counts = {}
for district in raw_districts:
    raw_counts[district] = raw_counts.get(district, 0) + 1
duplicates_raw = {d: count for d, count in raw_counts.items() if count > 1}
if duplicates_raw:
    for district, count in sorted(duplicates_raw.items()):
        print(f"{district}: appears {count} times")
else:
    print("None")

# Check for duplicate polling districts in ge2025_polling_districts_with_elector_size.geojson
print("\nDuplicate polling districts in ge2025_polling_districts_with_elector_size.geojson:")
processed_counts = {}
for district in processed_districts:
    processed_counts[district] = processed_counts.get(district, 0) + 1
duplicates_processed = {d: count for d, count in processed_counts.items() if count > 1}
if duplicates_processed:
    for district, count in sorted(duplicates_processed.items()):
        print(f"{district}: appears {count} times")
else:
    print("None")