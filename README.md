# Drawing Singapore's Electoral Boundaries



# Sources

The 2025 Polling Districts is annotated by Yudhishthra Nathan et al

`raw_data/ge2025_polling_districts.kml`
`raw_data/ge2025_smc_grc.kml`

- https://www.facebook.com/yudhishthra/posts/pfbid02SgcvubpES3Rh7ht32qjCc4KCUCMRbwe5ozvpBu6kx2uUHioQy4HtYd6bBhevhjLKl
- https://www.google.com/maps/d/u/0/viewer?mid=1FT8Te1iDvt4gNHZh2h6tLh7sDv_UkUg


The 2025 Electoral Boundary is downloaded from

`raw_data/ge2025_electoral_boundary.geojson`

- https://data.gov.sg/datasets/d_7ddf956dfc1c59080bf95bba1c58a5d2/view


The 2025 Elector Size is processed from

`raw_data/ge2025_electoral_divisions_and_polling_districts.json`
`raw_data/ge2025_polling_districts_and_elector_size.json`

- https://www.eld.gov.sg/pdf/White_Paper_on_the_Report_of_the_Electoral_Boundaries_Review_Committee_2025.pdf


# Inaccuracies

- HN17 should be merged into HN01
- NS21 should be craved from NS19
- SK18 shoudl be craved from SK17, and also some rearrangements in SK19 to SK23

For now I will work with the inaccuracies. This can be fixed later.


# Data processing pipeline

```
python3 scripts/fix_kml_boundaries.py  # Fixes KML boundaries and identifies quadripoints
python3 scripts/estimate_elector_size.py  # Estimates elector size for districts
python3 scripts/validate_input_data.py  # Validates input data
python3 scripts/generate_adjacent_districts.py  # Generates adjacency data, handling quadripoints properly
python3 scripts/add_elector_size_to_polling_districts.py  # Adds elector size data to polling districts
```

## Quadripoint Handling

A "quadripoint" is a location where 4 or more districts meet at a single point. At these locations, we need special handling to determine which districts should be considered adjacent. We've implemented a geometric approach that:

1. Identifies all points where 4+ districts meet
2. For each quadripoint, sorts the districts by their angular position around the point
3. Removes "false adjacencies" between districts that are opposite each other at the quadripoint

This prevents diagonal districts from being considered adjacent when they only touch at a single point. The analysis data is stored in `processed_data/quadripoint_analysis.txt` which shows all identified quadripoints and the adjacency decisions made.

# To run locally

```
python -m http.server
```