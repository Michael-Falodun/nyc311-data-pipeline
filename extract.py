
# ==========================================
# BLOCK 1: IMPORT LIBRARIES
# ==========================================

# Import libraries for API communication and data processing
import requests
import pandas as pd

# Import time for retry delays
import time

# Import json to read and write JSON files
import json

# Import tools for file management and timestamps
from pathlib import Path
from datetime import datetime


# ==========================================
# BLOCK 2: API CONFIGURATION
# ==========================================

# Define the NYC 311 API URL
url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"

# Define the number of records per request
limit = 1000

# Define the initial extraction size
total_records = 5000

# Configure error handling
max_retries = 3
retry_delay = 5

# Create an empty list for retrieved records
all_data = []


# ==========================================
# BLOCK 3: FOLDER AND CHECKPOINT SETUP
# ==========================================

# Locate the project folder
project_folder = Path(__file__).resolve().parent

# Define the raw data folder
raw_folder = project_folder / "data" / "raw"

# Create the folder if it does not exist
raw_folder.mkdir(parents=True, exist_ok=True)

# Define the checkpoint file location
checkpoint_path = project_folder / "data" / "checkpoint.json"

# Assume no previous checkpoint exists
last_created_date = None

# Check whether a checkpoint already exists
if checkpoint_path.exists():

    # Open and read the checkpoint file
    with checkpoint_path.open("r", encoding="utf-8") as file:
        checkpoint = json.load(file)

    # Retrieve the previous extraction timestamp
    last_created_date = checkpoint["last_created_date"]

    print(f"Previous checkpoint: {last_created_date}")

else:

    # No checkpoint means this is the first incremental run
    print("No checkpoint found. Starting initial extraction.")


# ==========================================
# BLOCK 4: AUTOMATED PAGINATION
# ==========================================

# Start at the first page
offset = 0

# Continue requesting records until finished
while True:

    # Define the API request parameters
    params = {
        "$limit": limit,
        "$offset": offset,
        "$order": "created_date DESC, unique_key DESC"
    }

    # If a checkpoint exists, request only newer complaints
    if last_created_date:
        params["$where"] = f"created_date > '{last_created_date}'"


    # ======================================
    # BLOCK 5: ERROR HANDLING AND RETRIES
    # ======================================

    # Attempt each API request up to three times
    for attempt in range(1, max_retries + 1):

        try:
            # Send the API request
            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            # Check whether the request succeeded
            response.raise_for_status()

            # Convert the response into Python data
            data = response.json()

            # Exit the retry loop after success
            break

        except requests.exceptions.RequestException as error:

            # Display the failed attempt
            print(f"Attempt {attempt} failed: {error}")

            # Stop if all attempts have failed
            if attempt == max_retries:
                raise

            # Wait before trying again
            time.sleep(retry_delay)

    # Add the retrieved records to our main list
    all_data.extend(data)

    # Display extraction progress
    print(f"Offset: {offset} | Retrieved: {len(data)} records")

    # Stop when the API returns fewer records than requested
    if len(data) < limit:
        break

    # Increase the offset for the next batch
    offset += limit

    # Limit the initial extraction to 5,000 records
    if last_created_date is None and offset >= total_records:
        break


# ==========================================
# BLOCK 6: CHECK FOR NEW DATA
# ==========================================

# Stop if there are no new records
if not all_data:

    print("No new records found.")
    print("Extraction complete.")

    # Exit the program successfully
    raise SystemExit(0)


# ==========================================
# BLOCK 7: DATAFRAME CONVERSION
# ==========================================

# Convert the retrieved records into a structured table
df = pd.DataFrame(all_data)

# Display the first five rows
print(df.head())


# ==========================================
# BLOCK 8: DATA PROFILING
# ==========================================

# Display dataset dimensions
print("Dataset dimensions:")
print(df.shape)

# Display column names
print("Column names:")
print(df.columns.tolist())

# Display data types
print("Data types:")
print(df.dtypes)

# Count missing values
print("Missing values:")
print(df.isnull().sum())

# Count duplicate complaint IDs
print("Duplicate records:")
print(df["unique_key"].duplicated().sum())


# ==========================================
# BLOCK 9: RAW DATA STORAGE
# ==========================================

# Generate a timestamp for the filename
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

# Create a unique file path
file_path = raw_folder / f"nyc311_{timestamp}.jsonl"

# Save the original API records directly
with file_path.open("w", encoding="utf-8") as file:

    for record in all_data:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

# Display the saved file location
print(f"Raw data saved to: {file_path}")


# ==========================================
# BLOCK 10: UPDATE CHECKPOINT
# ==========================================

# Identify the newest complaint creation date
latest_created_date = df["created_date"].max()

# Create the checkpoint information
checkpoint = {
    "last_created_date": latest_created_date,
    "last_extraction_time": datetime.now().isoformat(),
    "records_retrieved": len(all_data)
}

# Write checkpoint to a temporary file first
temporary_path = checkpoint_path.with_suffix(".tmp")

with temporary_path.open("w", encoding="utf-8") as file:
    json.dump(checkpoint, file, indent=4)

# Replace the checkpoint only after writing successfully
temporary_path.replace(checkpoint_path)

# Display the updated checkpoint
print(f"Checkpoint updated: {latest_created_date}")


# ==========================================
# BLOCK 11: EXTRACTION SUMMARY
# ==========================================

print("Extraction complete!")
print(f"Total records retrieved: {len(all_data)}")
print(f"Total columns: {len(df.columns)}")
