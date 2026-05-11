import os
from dotenv import load_dotenv
from app.influx import query as influx_query
from app.config import INFLUXDB_BUCKET

load_dotenv()

def check_temperature_exists():
    print(f"Searching for 'temperature' field in bucket: {INFLUXDB_BUCKET}...")
    # Query for any records with field 'temperature' in the last 30 days
    flux = f'from(bucket: "{INFLUXDB_BUCKET}") |> range(start: -30d) |> filter(fn: (r) => r._field == "temperature") |> limit(n:5)'

    try:
        tables = influx_query(flux)
        if not tables:
            print("No records found with field 'temperature' in this bucket.")
            return

        for table in tables:
            for record in table.records:
                # Use the record's internal values dictionary for access
                values = record.values
                measurement = values.get('_measurement')
                val = values.get('_value')
                time = values.get('_time')
                print(f"Found temperature data! Measurement: {measurement}, Value: {val}, Time: {time}")

    except Exception as e:
        print(f"Error querying InfluxDB: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_temperature_exists()
