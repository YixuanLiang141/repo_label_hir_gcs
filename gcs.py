import pandas as pd

def filter_large_csv_by_stay_ids(input_file, output_file, key_col, chunksize=100_000):
    valid_ids = [10000100, 10000200, 10000300]

    reader = pd.read_csv(input_file, chunksize=chunksize)
    first_chunk = True

    total_rows_kept = 0
    for i, chunk in enumerate(reader):
        filtered_chunk = chunk[chunk[key_col].isin(valid_ids)]
        total_rows_kept += len(filtered_chunk)

        if first_chunk:
            filtered_chunk.to_csv(output_file, index=False, mode='w')
            first_chunk = False
        else:
            filtered_chunk.to_csv(output_file, index=False, mode='a', header=False)

        print(f"Chunk {i+1} done. {len(filtered_chunk)} rows kept.")

def process_columns(input_csv, output_csv):

    df = pd.read_csv(input_csv)

    df = df[["observation_tables/", "patientid", "value", "variableid"]]
    df.rename(columns={'patientid': 'subject_id'}, inplace=True)
    df.rename(columns={'observation_tables/': 'charttime'}, inplace=True)
    df.rename(columns={'variableid': 'item'}, inplace=True)

    df = df.drop_duplicates(keep='first')

    mapping = {10000100: 'verbal', 10000200: 'motor', 10000300: 'eye'}
    df["item"] = df["item"].map(mapping).fillna(df["item"])

    # If different values exist in the same patient, time and category, get the smallest
    df = (
        df.sort_values("value", ascending=True, na_position="last", kind="stable")
        .drop_duplicates(subset=["subject_id", "charttime", "item"], keep="first")
        .sort_values(["subject_id", "charttime", "item"])
        .reset_index(drop=True)
    )

    df.to_csv(output_csv, index=False)
    print(f"Done, result save to: {output_csv}")

    return df

def calculate_gcs(input_path, output_path):
    """Calculate total GCS using original component scores within four hours."""

    df = pd.read_csv(input_path)


    required = {"subject_id", "charttime", "item", "value"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")

    df = df.loc[df["item"].isin(["eye", "motor", "verbal"])].copy()
    df["charttime"] = pd.to_datetime(
        df["charttime"], errors="raise"
    ).astype("datetime64[ns]")
    df["value"] = pd.to_numeric(df["value"], errors="raise")

    keys = ["subject_id", "charttime"]

    if df[keys].isna().any().any():
        raise ValueError("subject_id and charttime must not be missing.")

    # Keep every observed timestamp as a candidate for total GCS.
    candidates = (
        df[keys]
        .drop_duplicates()
        .sort_values(["charttime", "subject_id"])
        .reset_index(drop=True)
    )

    # Reject conflicting scores for the same timestamp and component.
    score_counts = df.groupby(keys + ["item"])["value"].nunique()
    conflicts = score_counts.loc[score_counts.gt(1)]

    if not conflicts.empty:
        raise ValueError(
            "Conflicting scores for the same subject, timestamp, and component:\n"
            f"{conflicts.head(10).to_string()}"
        )

    # Collapse identical duplicates and retain original numeric scores.
    sources = (
        df.dropna(subset=["value"])
        .groupby(keys + ["item"], as_index=False)["value"]
        .max()
    )

    for component in ("eye", "motor", "verbal"):
        source = sources.loc[
            sources["item"].eq(component),
            keys + ["value"],
        ].rename(columns={"value": component})

        if candidates.empty or source.empty:
            candidates[component] = float("nan")
            continue

        # Prefer exact matches, then the latest original score within four hours.
        # Filled scores never become sources for subsequent timestamps.
        candidates = pd.merge_asof(
            candidates.sort_values("charttime", kind="stable"),
            source.sort_values("charttime", kind="stable"),
            on="charttime",
            by="subject_id",
            direction="backward",
            tolerance=pd.Timedelta(hours=4),
            allow_exact_matches=True,
        )

    # Remove timestamps that still lack any component after filling.
    complete = candidates.dropna(subset=["eye", "motor", "verbal"]).copy()
    complete["value"] = complete[["eye", "motor", "verbal"]].sum(axis=1)

    result = (
        complete[keys + ["value"]]
        .sort_values(keys, kind="stable")
        .reset_index(drop=True)
    )

    result.to_csv(output_path, index=False)

    return result

if __name__ == "__main__":

    #filter_large_csv_by_stay_ids('../../hirid/observation_tables.csv', './gcs_raw.csv', 'variableid')
    #process_columns('./gcs_raw.csv', './gcs_raw.csv')
    calculate_gcs('./gcs_raw.csv', './gcs.csv')