from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from app.config import INFLUXDB_BUCKET, INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_ORG

_client: InfluxDBClient | None = None

def get_client() -> InfluxDBClient:
    global _client
    if _client is None:
        if not INFLUXDB_URL or not INFLUXDB_TOKEN or not INFLUXDB_ORG:
            raise RuntimeError(
                "Missing InfluxDB configuration: INFLUXDB_URL, INFLUXDB_TOKEN, and INFLUXDB_ORG must be set in .env"
            )
        _client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    return _client

def query(flux: str):
    client = get_client()
    return client.query_api().query(flux)


def write_point(point: Point, bucket: str = INFLUXDB_BUCKET):
    client = get_client()
    return client.write_api(write_options=SYNCHRONOUS).write(bucket=bucket, org=INFLUXDB_ORG, record=point)
