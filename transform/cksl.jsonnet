local schemaOrgContext = {
  '@context': 'https://schema.org',
};

local ASHWINI_LOCATION = {
  '@type': 'Place',
  'name': 'Choe Khor Sum Ling Centre, Ashwini',
  'address': 'No. 24, 1st floor, 3rd Main Rd, K.R.Colony, Domlur I Stage, Bengaluru, Karnataka 560071',
  'isicV4': '8549',
  'geo': {
    '@type': 'GeoCoordinates',
    'latitude': '12.9577059',
    'longitude': '77.6327838',
  },
};

local MONTFORT_LOCATION = {
  '@type': 'Place',
  'name': 'Montfort Spiritual Centre',
  'address': '184, Old Madras Rd, Binna Mangala, Indiranagar, Bengaluru, Karnataka 560038',
  'telephone': '+91 9141030564',
  'isicV4': '9491',
  'geo': {
    '@type': 'GeoCoordinates',
    'latitude': '12.9863008',
    'longitude': '77.64658',
  },
};

# Extract EID from @id (part before @google.com)
local extractEid(id) =
  if id != null && std.length(std.split(id, '@')) > 0 then
    std.split(id, '@')[0]
  else
    '';

# Determine location based on event name or existing location
local getLocation(event) =
  local name = if std.objectHas(event, 'name') then std.asciiLower(event.name) else '';
  local locName = if std.objectHas(event, 'location') && event.location != null && std.objectHas(event.location, 'name') then std.asciiLower(event.location.name) else '';
  local combined = name + ' ' + locName;
  if std.length(std.findSubstr('montfort', combined)) > 0 then
    MONTFORT_LOCATION
  else
    ASHWINI_LOCATION;

local transformEvent(event) =
  local eid = extractEid(event['@id']);
  local desc = if event.description == null || event.description == '' then
    'No further details available, please check with CKSL'
  else
    event.description;
  {
    '@type': 'Event',
    '@id': 'cksl:' + eid,
    name: event.name,
    url: 'https://cksl.in/?eid=' + eid + '#section3',
    startDate: event.startDate,
    endDate: event.endDate,
    description: desc,
    location: getLocation(event),
    keywords: ['CKSL'],
  } + schemaOrgContext;

function(INPUT) [
  transformEvent(event)
  for event in std.parseJson(INPUT)
  # Filter future events only
  if event.startDate >= std.native('today')()
]
