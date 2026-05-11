
import json
from typing import Any, Dict, List, Callable
from crewai.tools import BaseTool
from pydantic import Field

class InfluxDBQueryTool(BaseTool):
    name: str = "influxdb_query_tool"
    description: str = (
        "Executes Flux queries against InfluxDB to retrieve environmental data. "
        "Input should be a valid Flux query string. "
        "Returns a JSON string of the query results." 
    )
    # These will be set during initialization in crew.py
    influx_query_func: Callable[[str], Any] = Field(default=None, exclude=True)
    influx_bucket: str = Field(default=None, exclude=True)

    def _run(self, flux_query: str) -> str:
        if not self.influx_query_func or not self.influx_bucket:
            return json.dumps({"status": "error", "message": "InfluxDB client not initialized in tool."})

        try:
            # Replace placeholder with actual InfluxDB query
            results = self.influx_query_func(flux_query)
            
            # Influx results are "tall": each record is (time, field, value).
            # We reshape into "wide" JSON: one object per time with multiple fields.
            by_time: Dict[str, Dict[str, Any]] = {}
            for table in results:
                for record in table.records:
                    t = record.get_time().isoformat()
                    field = record.get_field()
                    value = record.get_value()
                    if t not in by_time:
                        by_time[t] = {"time": record.get_time().isoformat()}
                    by_time[t][field] = value
            
            # Convert dict->list, sort by time ascending
            reshaped_results = list(by_time.values())
            reshaped_results.sort(key=lambda x: x["time"])

            return json.dumps({"status": "success", "data": reshaped_results}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

# Factory alias — crew.py imports `influxdb_query_tool` and calls it with the
# runtime InfluxDB dependencies (query function + bucket).
influxdb_query_tool = InfluxDBQueryTool
