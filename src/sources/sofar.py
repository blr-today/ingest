import json
import datetime
import curl_cffi
from common.tz import IST
BROWSER_CODE = "safari184_ios"

def to_schema_org_music_event(event_info):
    base_url = "https://www.sofarsounds.com/events/"
    guestsArriveAt = datetime.datetime.fromisoformat(
        event_info.get("guestsArriveAt")
    ).astimezone(IST)
    startsAt = datetime.datetime.fromisoformat(event_info.get("startsAt")).astimezone(
        IST
    )
    # events are assumed to be 2 hours long
    endsAt = startsAt + datetime.timedelta(hours=2)
    try:
        name = event_info["theme"]["title"] + " Sofar concert at a "
    except:
        name = "Sofar concert"

    categories = ""
    neighbourhood = None
    try:
        categories = "/".join([x["name"] for x in event_info["venue"]["venueCategories"]])
    except TypeError:
        pass
    if categories != "Other":
        name += categories + " in "
    try:
        neighbourhood = event_info["venue"]["neighborhood"]["title"]
        name += event_info["venue"]["neighborhood"]["title"]
        # TODO: Check VenueName
    except Exception:
        name += event_info["city"]["title"]

    # Mapping the provided dictionary to schema.org format
    music_event_schema = {
        "url": f"{base_url}{event_info['id']}",
        "startDate": startsAt.isoformat(),
        "doorTime": guestsArriveAt.isoformat(),
        "endDate": endsAt.isoformat(),
        "name": name,
        "description": "An intimate concert by Sofar Sounds, at an offbeat venue. Venue details will be disclosed 36 hours before the event.",
        "location": {
            "@type": "Place",
            "address": neighbourhood or event_info["city"]["title"]
        },
        "image": event_info["imageUrl"],
        "remainingAttendeeCapacity": event_info["remainingSpaces"],
        "offers": {
            "@type": "Offer",
            "price": (event_info["ticketPrice"] + event_info["bookingFee"])/100,
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock",
        }
    }

    return music_event_schema


def make_graphql_request(query, city, url):
    body = curl_cffi.post(url, json={
            "operationName": "GetEventsForFanWithAttendees",
            "variables": {
                "city": city,
                "page": 1,
                "perPage": 2
            },
            "query": query,
        },impersonate=BROWSER_CODE).content
    return json.loads(body)


query = """
query GetEventsForFanWithAttendees(
  $city: String
  $page: Int
  $perPage: Int
) {
  events(
    city: $city
    upcoming: true
    published: true
    page: $page
    perPage: $perPage
  ) {
    events {
      attendeeFlow
      cancelled
      endsAt
      guestsArriveAt
      id
      isAppliable
      isPublished
      isPurchasable
      isSoldOut
      localStartsAt
      onPresale
      startsAt
      remainingSpaces
      ticketPrice
      bookingFee
      imageUrl
      city {
        title
        timezone
      }
      isVenueConfirmed
      neighborhood {
        title
      }
      venue {
        neighborhood {
          title
        }
        venueName
        venueCategories {
          name
        }
      }
      eventThemes {
        title
      }
    }
  }
}
"""
url = "https://www.sofarsounds.com/api/v2/graphql?on=GetEventsForFanWithAttendees"


def main():
    response = make_graphql_request(query, "bangalore", url)
    events = []
    for d in response["data"]["events"]["events"]:
        events.append(to_schema_org_music_event(d))
    with open("out/sofar.json", "w") as f:
        json.dump(events, f, indent=2)
    print(f"[SOFAR] {len(events)} events")


if __name__ == "__main__":
    main()
