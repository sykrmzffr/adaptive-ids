"""
preprocess.py - turn the 8 CIC-IDS2017 MachineLearningCSV files into
train/test arrays for the Random Forest.

Run from the project root:
    python training/preprocess.py

Input : data/**/*.pcap_ISCX.csv (the 8 original CSVs, e.g. in data/MachineLearningCVE/)
Output: data/processed.npz      (X_train, y_train, X_test, y_test - NOT SMOTE'd)
        data/preprocess_report.json
"""
import glob
import json
import os
import re

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# --- Settings you may change -------------------------------------------------
# Column names exactly as they appear in the CSVs (after stripping spaces).
# Table 3.7 features 1-11. Feature 12 (Destination Port Entropy) is not in
# the dataset, so it can't be here.
FEATURES = [
    "Flow Duration",                 # microseconds
    "Total Fwd Packets",
    "Total Backward Packets",
    "Total Length of Fwd Packets",
    "Total Length of Bwd Packets",
    "Fwd Packet Length Mean",
    "Bwd Packet Length Mean",
    "Flow Packets/s",
    "Flow Bytes/s",
    "SYN Flag Count",
    "RST Flag Count",
]
LABEL = "Label"
BINARY = True          # True: BENIGN=0 / everything else=1.  False: multi-class
TEST_SIZE = 0.20
SEED = 42
DATA_DIR = "data"
# -----------------------------------------------------------------------------


def load_all(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "**", "*.pcap_ISCX.csv"), recursive=True))
    if not files:
        raise SystemExit(f"No *.pcap_ISCX.csv files found in {data_dir}/")
    wanted = set(FEATURES + [LABEL])
    frames = []
    for f in files:
        # latin-1: the Thursday WebAttacks file has a non-UTF-8 dash in its labels.
        # usecols: only load the 12 columns we need (the full file is ~80 columns).
        df = pd.read_csv(f, encoding="latin-1", low_memory=False,
                         usecols=lambda c: c.strip() in wanted)
        df.columns = df.columns.str.strip()   # ' Flow Duration' -> 'Flow Duration'
        print(f"  {os.path.basename(f):60s} {len(df):>9,d} rows")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main():
    report = {}
    print("Loading CSVs ...")
    df = load_all(DATA_DIR)
    report["rows_loaded"] = len(df)

    # Clean up label text: 'Web Attack \x96 Brute Force' -> 'Web Attack - Brute Force'
    df[LABEL] = df[LABEL].astype(str).str.strip()
    df[LABEL] = df[LABEL].apply(lambda s: re.sub(r"[^\x20-\x7E]", "-", s))
    report["label_counts_raw"] = df[LABEL].value_counts().to_dict()

    # Force numeric (a few rows contain junk text), then drop inf / NaN
    X = df[FEATURES].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)
    bad = X.isna().any(axis=1)
    report["rows_dropped_inf_or_nan"] = int(bad.sum())
    df = pd.concat([X, df[LABEL]], axis=1)[~bad]

    # Negative durations / rates exist in the dataset; they're physically impossible
    neg = (df[FEATURES] < 0).any(axis=1)
    report["rows_dropped_negative"] = int(neg.sum())
    df = df[~neg]

    # Exact duplicate rows (same features AND same label)
    n0 = len(df)
    df = df.drop_duplicates()
    report["rows_dropped_duplicate"] = n0 - len(df)

    # Same features but DIFFERENT labels: the model can't learn these - drop them
    conflict = df.duplicated(subset=FEATURES, keep=False)
    report["rows_dropped_conflicting_label"] = int(conflict.sum())
    df = df[~conflict]

    if BINARY:
        y = (df[LABEL] != "BENIGN").astype(np.int8).to_numpy()
        classes = ["BENIGN", "ATTACK"]
    else:
        classes = sorted(df[LABEL].unique())
        y = df[LABEL].map({c: i for i, c in enumerate(classes)}).to_numpy()
    X = df[FEATURES].to_numpy(dtype=np.float64)
    report["rows_final"] = len(df)
    report["label_counts_final"] = df[LABEL].value_counts().to_dict()

    # Stratified split FIRST. SMOTE happens later, on the training part only.
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=SEED)
    report["train_rows"], report["test_rows"] = len(y_tr), len(y_te)

    np.savez_compressed(os.path.join(DATA_DIR, "processed.npz"),
                        X_train=X_tr, y_train=y_tr, X_test=X_te, y_test=y_te,
                        features=np.array(FEATURES), classes=np.array(classes))
    with open(os.path.join(DATA_DIR, "preprocess_report.json"), "w") as fh:
        json.dump(report, fh, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
