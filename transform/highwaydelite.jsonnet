local schemaOrgContext = {
  '@context': 'https://schema.org',
  '@type': 'SocialEvent',
};

local BASE_URL = 'https://biker.highwaydelite.com/';
local CLUBMAP;

local transformEvent(event, CLUBMAP) =
  {
    url: BASE_URL + "event/" + event.id,
    image: BASE_URL + event.bannerimage,
    name: "Bikers: " + event.name,
    description: std.native('html2text')(event.description) + ".\n This event is listed on Bikers Highwat Delite platform",
    location: {
      '@type': 'Place',
      name: "Bengaluru",
    },
    keywords: ["HIGHWAYDELITE"],
    startDate: date.concert_date,
    // "endDate": event.modified,
    eventStatus: 'EventScheduled',
  } + schemaOrgContext

function(INPUT) [
  CLUBMAP = { for club in INPUT.clubs: club.id => club },
  std.filterMap(filterEvent, transformEvent, std.parseJson(INPUT.events))
]
