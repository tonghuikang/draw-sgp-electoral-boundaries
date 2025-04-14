# Drawing Singapore's Electoral Boundaries



# Sources

The 2025 polling districts is annotated by Yudhishthra Nathan et al

`raw_data/ge2025_polling_districts.kml`

- https://www.facebook.com/yudhishthra/posts/pfbid02SgcvubpES3Rh7ht32qjCc4KCUCMRbwe5ozvpBu6kx2uUHioQy4HtYd6bBhevhjLKl
- https://www.google.com/maps/d/u/0/viewer?mid=1FT8Te1iDvt4gNHZh2h6tLh7sDv_UkUg


The 2025 elector sizes and district allocation is processed from

`raw_data/ge2025_electoral_divisions_and_polling_districts.json`
`raw_data/ge2025_polling_districts_and_elector_size.json`

- https://www.eld.gov.sg/pdf/White_Paper_on_the_Report_of_the_Electoral_Boundaries_Review_Committee_2025.pdf


The landmark data is processed from

- https://en.wikipedia.org/wiki/List_of_Singapore_MRT_stations
- https://data.humdata.org/dataset/hotosm_sgp_roads


# Inaccuracies

- NS21 should be craved from NS19
- SK18 should be craved from SK17

For now I will work with the inaccuracies. This can be fixed later.


# Data processing pipeline

```
rm intermediate_data/ge2025_polling_districts_fixed.kml
rm intermediate_data/mrt_stations_labeled.csv
rm intermediate_data/ge2025_polling_distrct_and_estimated_elector_size.json
rm intermediate_data/ge2025_polling_districts_to_adjacent_districts.json
rm processed_data/ge2025_polling_districts_with_information.geojson
rm annotations/*.json
source .venv/bin/activate
black -l 200 .
python3 scripts/fix_kml_boundaries.py
python3 scripts/label_mrt_stations.py
python3 scripts/estimate_elector_size.py
python3 scripts/generate_adjacent_districts.py
python3 scripts/add_information_to_polling_districts.py
python3 scripts/validate_input_data.py
python3 scripts/annotate_assignments.py
```


# To run locally

```
python -m http.server
```


# Fun facts

(to be verified)

- The dual of a planar graph is planar.
- There are approximately _ quadripoints and _ quintipoints.
- There _ pairs of boundaries that are opposite at quadripoints / quintipoints but are still adjacent somewhere.
- We give names to contituencies


# Comments appreciated

- If you think there is a criteria you think that you should factor in
- Tell me if you disagree if a polling district should belong to a certain area (TBC)
