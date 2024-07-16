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
    endDate: event.ends_at,
    url: event.url,
    sameAs: 'https://underline.center/t/' + event.post.id,
  };

function(INPUT) [
  transformEvent(event)
  for event in std.parseJson(INPUT).events
]
