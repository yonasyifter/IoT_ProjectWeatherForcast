import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
import firebase_admin
from firebase_admin import credentials

load_dotenv()

def test_influx():
    print("Testing InfluxDB...")
    url = os.getenv("INFLUXDB_URL")
    token = os.getenv("INFLUXDB_TOKEN")
    org = os.getenv("INFLUXDB_ORG")
    bucket = os.getenv("INFLUXDB_BUCKET")
    
    if not all([url, token, org, bucket]):
        print("Missing InfluxDB config")
        return
        
    try:
        client = InfluxDBClient(url=url, token=token, org=org)
        # Use Flux query for InfluxDB 2.x
        query = f'from(bucket: "{bucket}") |> range(start: -1h) |> limit(n:1)'
        client.query_api().query(query)
        print("✅ InfluxDB Token is WORKING")
    except Exception as e:
        print(f"❌ InfluxDB Token FAILED: {e}")
    finally:
        client.close() if 'client' in locals() else None

def test_firebase():
    print("Testing Firebase...")
    try:
        cert = {
            "type": "service_account",
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        # Check if already initialized
        try:
            firebase_admin.get_app()
        except ValueError:
            firebase_admin.initialize_app(credentials.Certificate(cert))
        print("✅ Firebase initialized successfully")
    except Exception as e:
        print(f"❌ Firebase FAILED: {e}")

if __name__ == "__main__":
    test_influx()
    test_firebase()
