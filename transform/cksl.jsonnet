local schemaOrgContext = {
  '@context': 'https://schema.org',
};

local BASE_URL = 'https://www.cksl.in/#calendar-51301a3b-7f76-429d-bcb5-98c6338857f4-event-';

local transformEvent(event) =
  {
    name: event.name + " (Choe Khor Sum Ling)",
    # This is a fake link, but we need something that points to tpcc.club
    # TODO: Add startepoch-endepoch
    url: BASE_URL + event.id,
    '@type': "Event",
    keywords: ['CKSL'] + if event.location == "6368b5fe33f56" then ["INDIRANAGAR"] else [],
    startDate: event.start.date + "T" + event.start.time + "+0530",
    endDate: event.end.date + "T" + event.end.time + "+0530",
    image: if event.image != null then event.image.url  else "",
    description: std.native('html2text')(event.description),
    location: {
      '@type': 'Place',
      "name": if event.location == "6368b5fe33f56" then {
        "name": "Choe Khor Sum Ling Centre",
        "address": "Ashwini, No. 24, 1st floor, 3rd Main Street, Domlur Layout 1st stage Bangalore 560071",
        "isicV4": "8549",
        "geo": {
          "latitude": "12.9577059",
          "longitude": "77.6327838"
        }
      } else if event.location == "6368b5fe33f92" then {
        "name": "Montfort Spiritual Centre",
        "address": "184, Old Madras Rd, Binna Mangala, Indiranagar, Bengaluru, Karnataka 560038",
        "telephone": "+91 9141030564",
        "isicV4": "9491",
        "geo": {
          "latitude": "12.9863008",
          "longitude": "77.64658"
        }
      }
    }
  } + schemaOrgContext;

function(INPUT) [
  transformEvent(event)
  for event in std.parseJson(INPUT).events
  # Drop Zoom events
  # or repeat events (typically daily meditation sessions)
  # and events in the past
  # or those with an epoch datetime
  if event.location != "6368b5fe33f0f" && event.repeatPeriod == "noRepeat" && std.type(event.start) == "object" && event.start.date >= std.native("today")()
]
