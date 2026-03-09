import pandas as pd

# Load the dataset
input_file = "Salary.csv"
df = pd.read_csv(input_file)

# Check if 'Race' column exists and remove it
if "Race" in df.columns:
    df = df.drop(columns=["Race"])
    print("'Race' column removed successfully.")
else:
    print("'Race' column not found.")

# Save the modified dataset
output_file = "Salary_no_race.csv"
df.to_csv(output_file, index=False)

print(f"Updated dataset saved as {output_file}")

