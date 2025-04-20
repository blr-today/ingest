local schemaOrgContext = {
  '@context': 'https://schema.org',
};

local BASE_URL = 'https://tpcc.club/events/';

local transformEvent(event) =
  {
    # This is a fake link, but we need something that points to tpcc.club
    url: BASE_URL + '#id=' + event.id,
    '@type': if event.theme == 'Book Reading' then 'LiteraryEvent' else 'ScreeningEvent',
    keywords: [event.theme, 'TPCC'],
    name: event.theme + ' - ' + event.title,
    [if event.theme != 'Book Reading' then 'workPresented']: {
      '@type': 'Movie',
      name: event.title,
      [if event.director !=null then "director"]: event.director,
    },
    startDate: event.date,
    image: event.image,
    [if event.link != null then 'sameAs']: event.link,
    location: event.location + {
      '@type': 'Place'
    }
  };

function(INPUT)[
  transformEvent(event)
  for event in (std.parseJson(INPUT))
]
