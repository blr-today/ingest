# parse in-known-hosts.yml
# pick eventbrite key
# eventbrite:
# pumarun:
#   id: "87498853333" 
#   keywords:
#     - PUMARUN
import yaml
from common import eventbrite

def write_urls(key, organizer_id):
    eb = eventbrite.EB(organizer_id)
    links = eb.fetch_links()
    with open(f"out/{key}.txt", "w") as f:
        for link in links:
            f.write(f"{link}\n")


with open("in/known-hosts.yml") as f:
    known_hosts = yaml.safe_load(f)
    for key, value in known_hosts["eventbrite"].items():
        write_urls(key, value["id"])
