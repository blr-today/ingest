import yaml
import json
import http.client

def get_event_urls(org_id):
    conn = http.client.HTTPSConnection("www.townscript.com")
    conn.request("GET", f"/listings/event/upcoming/userId/{org_id}")
    response = conn.getresponse()
    d = response.read().decode()
    for e in json.loads(d)['data']:
        yield f"https://www.townscript.com/e/{e['shortName']}"

def main():
    config = yaml.safe_load(open('in/known-hosts.yml'))['townscript']
    for c in config:
        for e in get_event_urls(config[c]['id']):
            print(e)

if __name__ == "__main__":
    main()