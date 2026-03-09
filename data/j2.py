import pandas as pd

# Load dataset
df = pd.read_csv("Salary.csv")

# Group by Job Title and compute statistics
job_title_stats = (
    df.groupby("Job Title")
      .agg(
          occurrences=("Salary", "count"),
          mean_salary=("Salary", "mean"),
          min_salary=("Salary", "min"),
          max_salary=("Salary", "max")
      )
      .reset_index()
)

# Sort by frequency (descending)
job_title_stats = job_title_stats.sort_values(
    by="occurrences",
    ascending=False
)

# Print all results
print("\nJob Title Salary Statistics (sorted by frequency)\n")
print(job_title_stats.to_string(index=False))

