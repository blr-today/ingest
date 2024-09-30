local schemaOrgContext = {
  '@context': 'https://schema.org',
  '@type': 'MusicEvent',
};

local BASE_URL = 'https://www.total-environment.com/music-and-events/';

local mapArtist(A, input) = [{
  '@type': 'MusicGroup',
  name: AD.artist_name,
  url: A.artist.artist_website,
  image: input.result.data.artist_media_path + A.artist.artist_picture,
  description: AD.artist_description,
} for AD in A.artist.artist_details];

local mapVenue(venue) = {
  '@type': 'Place',
  name: venue.restaurant_outlet.outlet_name,
  address: venue.restaurant_outlet.address,
};

# Input = "09:30 PM" 
# Output = "21:30:00"
local transformTime(time_str) =
  assert std.length(std.split(time_str, ':')) == 2 : 'Invalid time format';
  local time = std.split(time_str, ':');
  local minutes = std.split(time[1], ' ')[0];
  local hour = if std.endsWith(time[1], 'PM') then std.toString(std.parseInt(time[0]) + 12) else time[0];
  hour + ':' + minutes + ':00+05:30';

local transformEvent(event, input) = [
  assert std.length(event.music_event_venues) == 1 : 'Found more than one venue for event';
  {
    url: BASE_URL + event.url_slug,
    image: input.result.data.media_path + event.event_poster,
    name: event.music_event_details[0].event_name,
    description: std.native('html2text')(event.music_event_details[0].event_description),
    offers: [{
      '@type': 'Offer',
      price: event.standing_ticket_price,
      priceCurrency: 'INR',
      name: 'Standing',
    }, {
      '@type': 'Offer',
      price: event.seating_ticket_price,
      priceCurrency: 'INR',
      name: 'Seating',
    }],
    location: {
      '@type': 'Place',
      name: event.music_event_venues[0].restaurant_outlet.outlet_name,
      address: {
        '@type': 'PostalAddress',
        streetAddress: event.music_event_venues[0].restaurant_outlet.address + event.music_event_venues[0].city.city_name,
        // Should be Karnataka but that is not present
        // "addressRegion": event.music_event_venues[0].restaurant_outlet.area.area_name,
        addressLocality: event.music_event_venues[0].area.area_name,
        addressCountry: event.music_event_venues[0].country.country_name,
      },
    },
    performer: std.flattenArrays([mapArtist(A, input) for A in event.music_event_artists]),
    keywords: [G.genre.genre_name for G in event.music_event_genres] + ['WINDMILLS'],
    startDate: date.concert_date[0:10] + 'T' + transformTime(date.start_time),
    // "endDate": event.modified,
    eventStatus: 'EventScheduled',
  } + schemaOrgContext
  for date in event.music_event_venues[0].music_event_dates
];

function(INPUT) std.flattenArrays([
  transformEvent(event, std.parseJson(INPUT))
  for event in (std.parseJson(INPUT).result.data.music_events)
])
