import pandas as pd

# Load dataset
df = pd.read_csv("Salary.csv")

# Basic sanity check
print("Total records:", len(df))
print("Unique job titles:", df["Job Title"].nunique())
print("-" * 50)

# Group by Job Title
job_title_stats = (
    df.groupby("Job Title")
      .agg(
          count=("Salary", "count"),
          avg_salary=("Salary", "mean")
      )
      .reset_index()
)

# Sort by count (most frequent titles first)
job_title_stats = job_title_stats.sort_values(
    by="count",
    ascending=False
)

# Display top 20 job titles
print("Top 20 Job Titles by Frequency:\n")
print(job_title_stats.head(20).to_string(index=False))

print("\nBottom 20 Job Titles by Frequency:\n")
print(job_title_stats.tail(20).to_string(index=False))

# Optional: save for later inspection / Streamlit use
job_title_stats.to_csv("job_title_stats.csv", index=False)

print("\nSaved job_title_stats.csv")
	
