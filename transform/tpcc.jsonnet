// TPCC events are embedded on the website via
// elfsight. This is the widget ID on the elfsight backend.
local TPCC_CALENDAR_WIDGET_ID = 'da2c7ec1-91d2-4b82-a97b-43803ad416a2';

local schemaOrgContext = {
  '@context': 'https://schema.org',
};

local BASE_URL = 'https://tpcc.club/';

local geteventType(event, eventTypes) =
  local matchingEventTypes = [E.name for E in eventTypes if E.id == event.eventType];

  assert std.length(matchingEventTypes) == 1 : 'Found more than one eventType for event';
  matchingEventTypes[0];

local transformEvent(event, locations, eventTypes) =
  local startHour = std.parseInt(std.split(event.start.time, ':')[0]);
  local startMinute = std.parseInt(std.split(event.start.time, ':')[1]);
  // add 3 hours to startHour, since endTime upstream is same as startTime
  // @see https://talk.tpcc.club/t/event-calendar-improvements/48
  local endTime =
    if startHour + 3 < 24 then '%02d:%02d' % [startHour + 3, startMinute]
    else '23:59';

  local matchingLocations = [L for L in locations if L.id == event.location];
  assert std.length(matchingLocations) == 1 : 'Found more than one location for event';
  // .name holds BLR - Underline Center, so we drop the city name
  local locationName = std.split(matchingLocations[0].name, ' - ')[1];
  local cityID = std.split(matchingLocations[0].name, ' - ')[0];
  local locationAddress = std.strReplace(matchingLocations[0].address, locationName, '');
  local LA = if std.startsWith(locationAddress, ', ') then locationAddress[2:] else locationAddress;

  local category = geteventType(event, eventTypes);

  {
    url: BASE_URL + 'events/#calendar-' + TPCC_CALENDAR_WIDGET_ID + '-event-' + event.id,
    '@type': if category == 'Book Reading' then 'LiteraryEvent' else 'ScreeningEvent',
    keywords: [category, 'TPCC'],
    name: geteventType(event, eventTypes) + ' - ' + event.name,
    [if category != 'Book Reading' then 'workPresented']: {
      '@type': 'Movie',
      name: event.name,
    },
    description: std.native('html2text')(event.description),
    startDate: event.start.date + 'T' + event.start.time + ':00+05:30',
    endDate: event.end.date + 'T' + endTime + ':00+05:30',
    image: event.image.url,

    [if event.buttonLink.value != '' then 'offers']: {
      '@type': 'Offer',
      priceCurrency: 'INR',
      url: event.buttonLink.value,
    },
    [if event.buttonLink.value != '' then 'sameAs']: event.buttonLink.value,

    location: {
      '@type': 'Place',
      name: locationName,
      address: LA,
    }
  };

function(INPUT)
  local i = std.parseJson(INPUT);
  std.filter(function(e) std.member(e.location.address, 'Bangalore'), [
    transformEvent(event, i.locations, i.eventTypes)
    for event in (i.events)
  ])
