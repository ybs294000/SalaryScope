import pandas as pd

# Load dataset
df = pd.read_csv("Salary.csv")

# Group by Job Title and compute count + mean salary
summary = (
    df.groupby("Job Title")
      .agg(
          occurrences=("Salary", "count"),
          mean_salary=("Salary", "mean")
      )
      .reset_index()
)

# Sort by occurrences (descending)
summary = summary.sort_values(by="occurrences", ascending=False)

# Print nicely
print("\nJob Title Summary (sorted by frequency)\n")
print(summary.to_string(index=False))

