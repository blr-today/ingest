import http.client
import jsonpath
import json
import datefinder
import datetime
from urllib.parse import urlparse, parse_qs

# Public Key, not-logged-in API key
ZOMATO_API_KEY = "239899c6817b488ba5d82bbd49676a76"
def fetch_data(url, body):
    conn = http.client.HTTPSConnection("api.zomato.com")

    payload = json.dumps(body)

    headers = {
        'x-city-id': "4", # Bangalore
        'x-zomato-app-version': "17.43.5",
        'x-zomato-api-key': ZOMATO_API_KEY,
        'accept': "*/*",
        "user-agent": "gardencitybot/0.0.1"
    }

    conn.request("POST",url ,payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))


def qs(url, key='event_id'):
    q = urlparse(url).query
    v = parse_qs(q)[key][0]
    if 'zomaland' in url:
        return (v, True)
    return (v, False)

def get_event_ids():
    jsonpath_selector =  "$..['url']"
    data = fetch_data("/gw/goout/events/search", {
        "theme_type": "dark"
    })
    return list(set([ qs(url) for url in jsonpath.findall(jsonpath_selector, data) if 'event_id=' in url]))

def get_event_details(event_id, zomaland = False):
    url = "/gw/zlive/events/details"
    if zomaland:
        url = "/gw/zomaland/home"
    
    data = fetch_data(url, {
        "event_id": event_id
    })
    return data

def parse_datetime(dt):
    tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))  # Asia/Kolkata timezone
    print(dt)
    (start,end) = dt.split("-")
    r_start = None
    print(start)
    for d in list(datefinder.find_dates(start)):
        days = (d - datetime.datetime.now()).days
        if  days > 0 and days < 90:
            r_start = d
            break
    for dd in list(datefinder.find_dates(end, base_date = r_start)):
        r_end = dd
        break

    if r_start == None:
        return None

    # Move end by 1 day
    if r_end < r_start:
        r_end = r_end + datetime.timedelta(days=1)

    return (r_start.replace(tzinfo=tz).isoformat(), r_end.replace(tzinfo=tz).isoformat())

def make_event(event_id, data):
    text_sel = "$.results[0:-1]..['text']"
    d = jsonpath.findall(text_sel, data)
    r = {
        "title": d[0]
    }
    if d[1][0] == '₹':
        idx = 1
    else:
        r['subtitle'] = d[1]
        idx = 2
    r['cost'] = " ".join(d[idx:idx+2])
    r["datetime"] =  " ".join(d[idx+2:idx+4])
    r["venue"] = d[idx+4] if d[idx+4] != "To be Announced" else None
    r["event_id"] = event_id
    if len(d)>=idx+6:
        r['location'] = d[idx+5]
    if len(d)>=idx+8:
        r['description'] = d[idx+7]
    x = jsonpath.findall("$..[?(@.type == 'url_in_browser')]..url", data)
    if len(x)>0:
        r['url'] = x[0]
    # IF we have a URL, that is probably ticketing URL (insider/BMS) so we can get better data from there
    # IF not, let us check our datetime properly
    if 'url' not in r and 'onwards' not in r['datetime']:
        r['start'], r['end'] = parse_datetime(r['datetime'])
        if r['start'] == None:
            return None

    return r

if __name__ == "__main__":
    events = []
    for (e,zomaland) in get_event_ids():
        # Zomaland tickets show up via Insider anyway
        if not zomaland:
            jsonData = get_event_details(e, zomaland)
            event = make_event(e, jsonData)
            if event!=None:
                events.append(event)
    with open("out/zomato.json", "w") as f:
        json.dump(sorted(events, key=lambda x: x['event_id']), f, indent=2)
