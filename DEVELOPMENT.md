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


# To serve html locally

```
python -m http.server
```
