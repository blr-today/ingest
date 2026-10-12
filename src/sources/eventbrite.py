import sys
import yaml
from src.common import eventbrite


def write_urls(key, organizer_id):
    eb = eventbrite.EB(organizer_id)
    links = eb.fetch_links()
    with open(f"out/{key}.txt", "w") as f:
        for link in links:
            f.write(f"{link}\n")
    print(f"[EVENTBRITE/{key}] {len(links)} events", file=sys.stderr)


def main():
    with open("in/known-hosts.yml") as f:
        known_hosts = yaml.safe_load(f)
        org_key = sys.argv[1]
        org_id = known_hosts["eventbrite"][org_key]["id"]
        write_urls(org_key, org_id)


if __name__ == "__main__":
    main()
