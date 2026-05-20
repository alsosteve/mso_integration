from pathlib import Path
import pandas as pd
print("NEW VERSION RUNNING")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
file_path = PROJECT_ROOT / "data" / "raw" / "hosp10-reports" / "HOSP10_PRVDR_ID_INFO.CSV"

cols = pd.read_csv(file_path, nrows=0).columns.tolist()

for i, col in enumerate(cols, start=1):
    print(f"{i}: {col}")