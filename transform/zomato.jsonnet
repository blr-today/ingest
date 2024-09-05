local STATUSMAP = {
  SCHEDULED: 'EventStatusScheduled',
  CANCELLED: 'EventCancelled',
};

local AVAILABILITYMAP = {
  INSTOCK: 'InStock',
  SELLING_FAST: 'InStock',
  SOLDOUT: 'Sold Out',
};

local ATTENDANCEMAP = {
  OFFLINE: 'OfflineEventAttendanceMode',
};

local mapVenue(venue) = {
  '@type': 'Place',
  name: venue.restaurant_outlet.outlet_name,
  address: venue.restaurant_outlet.address,
};

local fixDate(date) = std.strReplace(date, ' ', 'T') + '+05:30';

local transformEvent(event) = {
  '@type': 'Event',
  '@context': 'https://schema.org',
  name: event.name,
  description: event.description,
  startDate: event.startDate,
  endDate: event.endDate,
  eventStatus: STATUSMAP[event.eventStatus],
  eventAttendanceMode: ATTENDANCEMAP[event.eventAttendanceMode],
  # This seems to only apply to TBA venues.
  # since we want this to be marked as within BLR, we use a generic BLR location for now.
  location: if std.objectHas(event, 'location') then event.location else {
    '@type': 'Place',
    'address': 'Bangalore'
  },
  
  isAccessibleForFree: event.isAccessibleForFree,
  image: event.images[0],
  offers: [
    {
      validFrom: fixDate(x.validFrom),
      availability: AVAILABILITYMAP[x.availability],
      priceCurrency: x.currency,
      eligibleQuantity: {
        value: x.inventory,
        '@type': 'QuantitativeValue',
      },
    }
    for x in event.tickets
  ],
  performers: event.performers,
  organizer: event.organizer,
  url: event.url,
  [if std.length(event.tickets) == 1 then 'remainingAttendeeCapacity']: event.tickets[0].inventory,
};
function(INPUT) [
  transformEvent(event)
  for event in std.parseJson(INPUT)
]
