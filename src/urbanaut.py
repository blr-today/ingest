import json
import http.client
import urllib
import time

TYPESENSE_API_KEY = "AYJefn98eRjmkyENmOlleSaqbXXQDKG6"

def scrape_urbanaut(categories="12"):
    ts = int(time.time())
    conn = http.client.HTTPSConnection("search.urbanaut.app")

    headers = {"x-typesense-api-key": TYPESENSE_API_KEY}
    querystring = {
        "q": "*",
        "page": "1",
        "per_page": "100",
        "filter_by": f"enable_list_view:=true && city:=Bengaluru && categories:=[{categories}] && (end_timestamp:>={ts} || has_end_timestamp:false )",
        "sort_by": "order:asc",
    }

    conn.request(
        "GET",
        "/collections/spot_approved/documents/search?"
        + urllib.parse.urlencode(querystring),
        headers=headers,
    )

    response = conn.getresponse()
    return json.loads(response.read().decode('utf-8'))

if __name__ == "__main__":
    with open("out/urbanaut.json", "w") as f:
        json.dump(scrape_urbanaut(), f, indent=2)
