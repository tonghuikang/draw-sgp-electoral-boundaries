#!/usr/bin/env python3
import json
import os

# Input and output file paths
script_dir = os.path.dirname(os.path.abspath(__file__))
input_file = os.path.join(script_dir, "../raw_data/ge2025_polling_districts_and_elector_size.json")
output_file = os.path.join(
    script_dir,
    "../intermediate_data/ge2025_polling_distrct_and_estimated_elector_size.json",
)

# Create a dictionary to store the estimated elector size for each polling district
district_to_size = {}

# Read the input file
with open(input_file, "r") as f:
    data = json.load(f)

# Process each constituency division
for division in data:
    elector_size = division["elector_size"]
    polling_districts = division["polling_districts"]
    num_districts = len(polling_districts)

    # Calculate base size and remainder
    base_size = elector_size // num_districts
    remainder = elector_size % num_districts

    # Distribute electors so each district gets base_size,
    # and the first 'remainder' districts get one extra elector
    for i, district in enumerate(polling_districts):
        if i < remainder:
            district_to_size[district] = base_size + 1
        else:
            district_to_size[district] = base_size

# Convert the dictionary to the desired output format
output_data = [{"polling_district": pd, "estimated_elector_size": size} for pd, size in district_to_size.items()]

# Write the output to a JSON file
with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Processed {len(district_to_size)} polling districts.")
print(f"Output written to {output_file}")
