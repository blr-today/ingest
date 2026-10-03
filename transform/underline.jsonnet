local transformEvent(event) =
  // Field names cannot see object locals, so these sit outside it
  local description = std.get(event, 'description', '');
  local image = std.get(event, 'image_upload', null);
  local links = std.get(event, 'links', []);
  {
    local title = event.post.topic.title,
    // Search for events with Cinema Club in title
    local cinema =
      std.length(std.findSubstr('cinema club', std.asciiLower(title))) > 0,
    local topic = event.post.topic,
    '@context': 'https://schema.org',
    '@type': if cinema then 'ScreeningEvent' else 'SocialEvent',
    startDate: event.starts_at,
    keywords: ['UNDERLINE', 'INDIRANAGAR'],
    name: title,
    [if event.ends_at != null then 'endDate']: event.ends_at,
    // Ticket links go in sameAs, so dedup can merge with their listings
    url: 'https://underline.center/t/' + std.get(topic, 'slug', 'topic') + '/' + topic.id,
    [if std.length(links) > 0 then 'sameAs']: links,
    [if description != null && description != '' then 'description']: description,
    [if image != null then 'image']: image.url,
    [if std.objectHas(event, 'offers') then 'offers']: event.offers,
    inLanguage: 'en',
    eventStatus: 'EventScheduled',
    maximumAttendeeCapacity: 45,
    maximumPhysicalAttendeeCapacity: 45,
    eventAttendanceMode: 'OfflineEventAttendanceMode',
    location: {
      '@type': 'Place',
      name: 'Underline Center',
      geo: {
        '@type': 'GeoCoordinates',
        latitude: 12.9672549,
        longitude: 77.6367397,
      },
      
      address: {
        '@type': 'PostalAddress',
        streetAddress: '3rd Floor, above Blue Tokai 24, 3rd A Cross, 1st Main Rd',
        addressLocality: 'Bangalore',
        postalCode: '560071',
        addressRegion: 'KA',
        addressCountry: 'IN',
      },
    },
  };

function(INPUT) [
  transformEvent(event)
  for event in std.parseJson(INPUT).events
  if !std.get(event, 'is_expired', false)
]
