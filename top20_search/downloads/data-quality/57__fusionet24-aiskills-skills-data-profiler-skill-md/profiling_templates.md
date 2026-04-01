# Data Profiling Templates

## Quick Profile Template

```python
import pandas as pd

# Load data
df = pd.read_parquet("data.parquet")  # or read_csv, read_json

# Quick profile
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print(f"\nInfo:")
df.info()
print(f"\nStats:")
print(df.describe())
print(f"\nNull counts:")
print(df.isnull().sum())
print(f"\nDuplicates: {df.duplicated().sum()}")
```

## CSV Profiling Template

```python
import pandas as pd

def profile_csv(file_path: str) -> dict:
    df = pd.read_csv(file_path)
    return {
        'rows': len(df),
        'columns': len(df.columns),
        'dtypes': df.dtypes.astype(str).to_dict(),
        'nulls': df.isnull().sum().to_dict(),
        'sample': df.head(5).to_dict('records')
    }
```

## JSON Profiling Template

```python
import pandas as pd

def profile_json(file_path: str) -> dict:
    df = pd.read_json(file_path, lines=True)  # For JSON Lines
    return {
        'rows': len(df),
        'columns': list(df.columns),
        'schema': [{
            'name': col,
            'type': str(df[col].dtype),
            'nulls': int(df[col].isnull().sum())
        } for col in df.columns]
    }
```

## Parquet Profiling Template

```python
import os
import pandas as pd
import pyarrow.parquet as pq

def profile_parquet(file_path: str) -> dict:
    # Read metadata without loading full file
    parquet_file = pq.ParquetFile(file_path)
    schema = parquet_file.schema_arrow

    # Load data for profiling
    df = pd.read_parquet(file_path)

    return {
        'file_size_mb': os.path.getsize(file_path) / (1024*1024),
        'rows': len(df),
        'columns': len(df.columns),
        'schema': str(schema),
        'statistics': df.describe().to_dict()
    }
```
