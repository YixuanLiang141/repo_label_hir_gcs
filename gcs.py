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

def merge_rename(input_csv, output_csv):

    df = pd.read_csv(input_csv)

    df = df[["observation_tables/", "patientid", "value", "variableid"]]
    df.rename(columns={'patientid': 'subject_id'}, inplace=True)
    df.rename(columns={'observation_tables/': 'charttime'}, inplace=True)
    df.rename(columns={'variableid': 'item'}, inplace=True)

    df = df.drop_duplicates(keep='first')

    mapping = {10000100: 'Verbal', 10000200: 'Motor', 10000300: 'Eyes'}
    df["item"] = df["item"].map(mapping).fillna(df["item"])

    df.to_csv(output_csv, index=False)
    print(f"Done, result save to: {output_csv}")

    return df

if __name__ == "__main__":

    #filter_large_csv_by_stay_ids('../../hirid/observation_tables.csv', './gcs.csv', 'variableid')
    merge_rename('./gcs.csv', './gcs2.csv')