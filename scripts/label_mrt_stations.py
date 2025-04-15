#!/usr/bin/env python3
import re
import pandas as pd
import os


def label_mrt_stations():
    # Get absolute path to ensure file is found
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    stations_path = os.path.join(root_dir, "raw_data", "stations.csv")

    # Load the station data
    df = pd.read_csv(stations_path)

    # Label "minor" stations: opened and >6000 passengers
    # 6000 is kind of arbitrary
    # Marymount and Mountbatten footfall is slightly more than 6000
    df["is_minor_mrt"] = df["is_opened"] & (df["passengers"] > 6000)

    # -- Prepare a helper dataframe to break down station_code into its line components.
    # Some stations may belong to multiple lines (e.g. "NS22 TE14")
    rows = []
    for idx, row in df.iterrows():
        code = row["station_code"]
        # split by space if multiple codes present
        parts = code.split()
        for part in parts:
            # extract alphabetical line code and numeric part (ignore trailing letters)
            m = re.match(r"([A-Z]+)(\d+)", part)
            if m:
                line = m.group(1)
                num = int(m.group(2))
                rows.append(
                    {
                        "station_idx": idx,  # reference to original df row index
                        "line": line,
                        "num": num,
                        "passengers": row["passengers"],
                    }
                )
    # Create a helper DataFrame for line information.
    df_lines = pd.DataFrame(rows)

    # For each line group, sort by the numeric part and determine if a station is a 'peak'
    # (has more passengers than its previous and next station along that line).
    def mark_peak(group):
        # sort by numeric order ("num")
        group = group.sort_values("num")
        # Use shift to get previous and next passengers for comparison.
        group = group.copy()
        group["prev_psg"] = group["passengers"].shift(1)
        group["next_psg"] = group["passengers"].shift(-1)
        # A station is a peak if it is not the first or last in the sorted order and
        # its passenger count is strictly greater than both its neighbors.
        group["is_peak"] = False
        # Only consider rows that have both neighbors (i.e. not NaN from the shift)
        mask = group["prev_psg"].notna() & group["next_psg"].notna()
        group.loc[mask, "is_peak"] = (group.loc[mask, "passengers"] > group.loc[mask, "prev_psg"]) & (group.loc[mask, "passengers"] > group.loc[mask, "next_psg"])
        return group

    # Process each line group separately to avoid the deprecation warning
    result_dfs = []
    for line, group in df_lines.groupby("line"):
        result_dfs.append(mark_peak(group))
    df_lines = pd.concat(result_dfs)

    # For each original station, if it is a peak on any line it appears in then mark it as peak.
    # We create a Series mapping station_idx to a boolean that is True if any row with that index is peak.
    peak_station = df_lines.groupby("station_idx")["is_peak"].any()

    # Create a new column in the original dataframe for major stations:
    # It must be opened, have >10000 passengers, and appear as a peak in at least one line.
    df["is_major_mrt"] = df["is_opened"] & (df["passengers"] > 10000) & df.index.to_series().map(peak_station).fillna(False)

    # Filter the dataframe to include only stations that are either minor or major.
    df_output = df.loc[
        df["is_minor_mrt"] | df["is_major_mrt"],
        ["name", "lat", "long", "is_minor_mrt", "is_major_mrt", "passengers"],
    ]

    # Save the output to CSV
    output_path = os.path.join(root_dir, "intermediate_data", "mrt_stations_labeled.csv")
    df_output.to_csv(output_path, index=False)
    print(f"Labeled MRT stations saved to {output_path}")


if __name__ == "__main__":
    label_mrt_stations()
