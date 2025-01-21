import pandas as pd

def load_and_prepare_datasets():
    dataset_files = [
        "daily_requests_2015Q1.csv",
        "daily_requests_2015Q2.csv",
        "daily_requests_2015Q3.csv",
    ]
    datasets = [pd.read_csv(file, delimiter=",", encoding="utf-8") for file in dataset_files]
    return datasets

