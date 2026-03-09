import pandas as pd

# --------------------------------------------------
# Load dataset
# --------------------------------------------------
df = pd.read_csv("data/Salary.csv")

pd.set_option("display.max_colwidth", 120)
pd.set_option("display.float_format", "{:,.2f}".format)

print("\n=== BASIC DATASET OVERVIEW ===")
print("Total records:", len(df))
print("Total columns:", df.shape[1])

# --------------------------------------------------
# Unique value counts per column
# --------------------------------------------------
print("\n=== UNIQUE VALUE COUNTS PER COLUMN ===\n")

unique_counts = (
    df.nunique(dropna=False)
      .reset_index()
      .rename(columns={"index": "Column", 0: "Unique Values"})
)

print(unique_counts.to_string(index=False))

# --------------------------------------------------
# Identify numerical columns
# --------------------------------------------------
numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

print("\n=== NUMERICAL COLUMNS IDENTIFIED ===")
print(numeric_cols)

# --------------------------------------------------
# Numerical statistics
# --------------------------------------------------
print("\n=== NUMERICAL COLUMN STATISTICS ===\n")

numeric_stats = df[numeric_cols].agg(
    ["count", "mean", "median", "min", "max"]
).transpose()

print(numeric_stats)

# --------------------------------------------------
# Unique values per column (controlled output)
# --------------------------------------------------
print("\n=== UNIQUE VALUES PER COLUMN ===\n")

MAX_SHOW = 30  # limit printed values per column

for col in df.columns:
    uniques = df[col].dropna().unique()
    count = len(uniques)

    print(f"\n--- {col} ({count} unique values) ---")

    if count <= MAX_SHOW:
        print(sorted(uniques))
    else:
        print(sorted(uniques[:MAX_SHOW]))
        print(f"... ({count - MAX_SHOW} more not shown)")

