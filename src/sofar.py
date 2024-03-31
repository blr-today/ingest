import http.client
import datetime
import json

tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def to_schema_org_music_event(event_info):
    base_url = "https://www.sofarsounds.com/events/"
    guestsArriveAt = datetime.datetime.fromisoformat(
        event_info.get("guestsArriveAt")
    ).astimezone(tz)
    startsAt = datetime.datetime.fromisoformat(event_info.get("startsAt")).astimezone(
        tz
    )
    # events are assumed to be 2 hours long
    endsAt = startsAt + datetime.timedelta(hours=2)

    venue = ""
    categories = "/".join([x["name"] for x in event_info["venue"]["venueCategories"]])
    if categories != "Other" :
        venue = categories + " in "
    venue += event_info["venue"]["neighborhood"]["title"]

    # Mapping the provided dictionary to schema.org format
    music_event_schema = {
        "@context": "http://schema.org",
        "@type": "MusicEvent",
        "url": f"{base_url}{event_info['id']}",
        "startDate": startsAt.isoformat(),
        "doorTime": guestsArriveAt.isoformat(),
        "endDate": endsAt.isoformat(),
        "location": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Bangalore",
                "addressRegion": "KA",
                "addressCountry": "IN",
                "streetAddress": venue,
            },
            "keywords": event_info["venue"]["venueType"],
        },
    }

    return music_event_schema


def make_graphql_request(query, city, url):
    headers = {"Content-Type": "application/json"}
    body = json.dumps(
        {
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
        }
    )

    conn = http.client.HTTPSConnection("www.sofarsounds.com")

    conn.request("POST", "/api/v2/graphql?on=GetEventsForCityPage", body, headers)

    data = json.loads(conn.getresponse().read())
    conn.close()

    return data


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
url = "https://example.com/graphql"


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
