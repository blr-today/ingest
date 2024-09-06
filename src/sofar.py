import json
import datetime
from common.session import get_cached_session
from common.tz import IST


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
        }
    }

    return music_event_schema


def make_graphql_request(query, city, url):
    session = get_cached_session()
    response = session.post(
        url,
        json={
            "operationName": "GetEventsForCityPage",
            "variables": {
                "city": city,
                "excludeCancelled": True,
                "excludeNonPresale": False,
                "excludePresale": False,
                "excludeSoldOut": False,
                "globallyPromoted": True,
                "includeNearbySecondaryCities": False,
                "loadDynamicHeaderImages": False,
                "page": 1,
                "perPage": 12,
                "published": True,
                "skipPagination": False,
                "upcoming": True,
            },
            "query": query,
        },
    )

    return response.json()


query = """
query GetEventsForCityPage(
  $city: String
  $includeNearbySecondaryCities: Boolean
  $neighborhood: String
  $date: String
  $excludeSoldOut: Boolean
  $excludePresale: Boolean
  $excludeNonPresale: Boolean
  $indoorOutdoor: String
  $isByob: Boolean
  $upcoming: Boolean
  $published: Boolean
  $globallyPromoted: Boolean
  $type: String
  $loadDynamicHeaderImages: Boolean
  $page: Int
  $perPage: Int
  $skipPagination: Boolean
) {
  events(
    city: $city
    includeNearbySecondaryCities: $includeNearbySecondaryCities
    neighborhood: $neighborhood
    date: $date
    excludeSoldOut: $excludeSoldOut
    excludePresale: $excludePresale
    excludeNonPresale: $excludeNonPresale
    indoorOutdoor: $indoorOutdoor
    isByob: $isByob
    upcoming: $upcoming
    published: $published
    globallyPromoted: $globallyPromoted
    type: $type
    loadDynamicHeaderImages: $loadDynamicHeaderImages
    page: $page
    perPage: $perPage
    skipPagination: $skipPagination
  ) {
    events {
      id
      guestsArriveAt
      localStartsAt
      startsAt
      onPresale
      isAppliable
      isPublished
      isPurchasable
      cancelled
      isSoldOut
      city {
        title
        timezone
      }
      isVenueConfirmed
      genres
      neighborhood {
        title
      }
      venue {
        neighborhood {
          title
        }
        venueType
        venueCategories {
          name
        }
      }
      theme {
        title
      }
    }
  }
}
"""
url = "https://www.sofarsounds.com/api/v2/graphql?on=GetEventsForCityPage"


def main():
    response = make_graphql_request(query, "bangalore", url)
    events = []
    for d in response["data"]["events"]["events"]:
        events.append(to_schema_org_music_event(d))
    # write to out/sofar.json
    with open("out/sofar.json", "w") as f:
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    main()
