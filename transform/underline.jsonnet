local transformEvent(event) =
  {
    local title = event.post.topic.title,
    // Search for events with Cinema Club in title
    local cinema =
      std.length(std.findSubstr('cinema club', std.asciiLower(title))) > 0,
    '@context': 'https://schema.org',
    '@type': if cinema then 'ScreeningEvent' else 'SocialEvent',
    startDate: event.starts_at,
    keywords: ['UNDERLINE', 'INDIRANAGAR'],
    name: title,
    [if event.ends_at != null then 'endDate']: event.ends_at,
    url: event.url,
    sameAs: 'https://underline.center/t/' + event.post.id,
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
]
