local transformOffer(offer, slug) = {
  '@type': 'Offer',
  # price: offer.converted_price_data.converted_amount,
  # priceCurrency: offer.converted_price_data.currency_symbol,
  availability: if std.get(offer, "quantity_left", 0) > 0 then 'InStock' else 'SoldOut',
  [if std.objectHas(offer, "ticket_name") then "name" else null]: offer.ticket_name,
  url: 'https://www.skillboxes.com/events/ticket/' + slug,
  [if std.objectHas(offer, "quantity_left") then "inventoryLevel" else null]: offer.quantity_left,
  [if std.length(offer.label_1) > 0 then "description" else null]: offer.label_1 + "\n" + offer.label_2,
};

# Returns a valid schema.org/Event object
local transformEvent(event) = {
  "@type": if event.category_name == "Party or Social Gathering" then "SocialEvent" 
  	else if event.category_name == "Music Events" then "MusicEvent"
  	else if event.category_name == "DJ/Producer" then "MusicEvent"
  	else if event.category_name == "Workshops" then "EducationEvent"
  	else "Event",
  "@context": 'https://schema.org',
  name: event.event_display_name,
  description: event.meta_description,
  startDate: event.starttime_ldjson,
  endDate: event.endtime_ldjson,
  location: {
    "@type": 'Place',
    name: event.venue_name,
    address: event.venue_address,
    [if event.venue_latitude !="0" then "geo" else null]: {
      "@type": 'GeoCoordinates',
      latitude: event.venue_latitude,
      longitude: event.venue_longitude
    }
  },
  keywords: [event.category_name],
  image: event.meta_event_cover_image,
  offers: [
    transformOffer(offer, event.slug)
    for offer in event.tickets
  ],
  isAccessibleForFree: event.is_free_ticket,
  "identifier": "com.skillboxes." + event.EventId,
  url: event.share_url,
};


function(INPUT) [
  transformEvent(event)
  for event in std.parseJson(INPUT)
]
