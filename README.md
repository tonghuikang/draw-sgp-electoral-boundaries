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
python3 scripts/fix_kml_boundaries.py
python3 scripts/estimate_elector_size.py
python3 scripts/validate_input_data.py
python3 scripts/generate_adjacent_districts.py
python3 scripts/add_elector_size_to_polling_districts.py
```


# To run locally

```
python -m http.server
```