import base64
import json
import os
import sqlite3
import sys
import time
import urllib.request

PATH = "/api/v1/push/influx/write"


def lines():
    status = os.environ.get("BUILD_STATUS", "success")
    duration = int(time.time()) - int(os.environ.get("BUILD_START", time.time()))
    runner = os.environ.get("RUNNER_ENVIRONMENT", "unknown")
    yield f"ingest_build,runner={runner} success={int(status == 'success')},duration_seconds={duration}"

    if os.path.exists("report.json"):
        with open("report.json") as f:
            report = json.load(f)
        fields = {**report["stats"], "unsupported_image_hosts": report.get("unsupported_image_hosts", 0)}
        yield "ingest_validation " + ",".join(f"{k}={v}" for k, v in fields.items())

    if os.path.exists("events.db"):
        conn = sqlite3.connect("events.db")
        rows = conn.execute(
            "SELECT substr(url, 9, instr(substr(url, 9), '/') - 1) AS source, COUNT(*) FROM events GROUP BY source"
        )
        for source, count in rows:
            if source:
                yield f"ingest_events,source={source} count={count}"
        conn.close()


def push(body):
    url = os.environ["GRAFANA_INFLUX_URL"].rstrip("/") + PATH
    auth = f"{os.environ['GRAFANA_INFLUX_USER']}:{os.environ['GRAFANA_INFLUX_TOKEN']}"
    req = urllib.request.Request(url, data=body.encode(), method="POST")
    req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(req, timeout=10) as res:
        print(f"Pushed {body.count(chr(10)) + 1} lines: HTTP {res.status}")


if __name__ == "__main__":
    body = "\n".join(lines())
    if "--dry-run" in sys.argv or not os.environ.get("GRAFANA_INFLUX_TOKEN"):
        print(body)
        sys.exit(0)
    try:
        push(body)
    except Exception as e:
        # Metrics must never fail the build
        print(f"::warning::Could not push metrics: {e}")
