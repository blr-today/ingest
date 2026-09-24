-- Description: This script is executed before the build of the database
-- json_replace is a no-op on missing keys, so give every event a keywords array
UPDATE events SET event_json = json_set(event_json, '$.keywords', json('[]'))
WHERE json_type(event_json, '$.keywords') IS NULL;

-- Small World is not a good venue
-- See 1/2 star rated reviews of their workshop at https://maps.app.goo.gl/UykxKFSYSgsEU6qCA
-- Urban Solace is a good venue, but their events are all food discounts essentially.
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  event_json ->> '$.location.name' LIKE '%small world%'
  OR event_json ->> '$.name' LIKE '%small world%'
  -- Gilly Super Bar in St Mark's Road is hosting mostly DJ nights
  -- and Small World events.
  OR ( 
    event_json ->> '$.location.name' LIKE '%gilly%'
    AND event_json ->> '$.location' LIKE '%super bar%'
    AND event_json ->> '$.location' LIKE '%st mark%'
  )
  -- This is also small world
  OR event_json ->> '$.organizer.name' LIKE '%flatworld ventures%'
  -- HighApe event listings do not include the organizer field 
  -- But we pick it up from meta tags into keywords
  -- This is no longer true, sadly
  OR event_json ->> '$.keywords' LIKE '%small world%'
  OR event_json ->> '$.organizer.name' LIKE '%urban solace%'
  -- These look like Small World events at Social venues
  -- But even if they aren't, the reviews are very bad.
  -- And sound exactly like the Small world reviews
  OR event_json ->> '$.organizer.name' LIKE '%growth sailor%'
  -- Silly dating events: https://district.in/free-speed-dating-events-in-bengaluru-sep7-2024/event
  OR event_json ->> '$.organizer.name' LIKE '%your dream partner%'
  -- Silly dating events on district
  OR event_json ->> '$.organizer.name' LIKE '%vinit kotadiya%'
  -- It is a cool well-reviewed venue in Jayanagar
  -- But you can drop by any day and do almost any workshop anyway.
  -- https://maps.app.goo.gl/8LBm3zjMRM3VS71E8
  -- https://highape.com/bangalore?search=Know+How
  OR event_json ->> '$.organizer.name' LIKE '%Know How%'
  -- Disha is the organizer at Know How.
  OR event_json ->> '$.organizer.name' LIKE '%Disha Gangadhar%'
  -- Also art events of unknown quality but there's a lot of them.
  OR event_json ->> '$.organizer.name' LIKE '%ANSHUL SUNDER SHARMA%'
  -- Same: Lots of art events always happening
  OR event_json ->> '$.organizer.name' LIKE '%STORYZONE%'
  OR event_json ->> '$.organizer.name' LIKE '%ZIEL RIFLE SOCIETY%'
  
  -- Silly dating event organizer: https://district.in/search?q=Rashid%20Mubarak%20Nadaf
  OR event_json ->> '$.organizer.name' LIKE '%rashid mubarak nadaf%';


-- BIC lists their events on District, but we have their original calendar
-- BCC lists their events on District, but we have their original calendar
DELETE FROM events
WHERE
  lower(event_json ->> '$.organizer.name') IN (
    'bangalore international centre',
    'tarun rajendra mittal (bangalore chess club)',
    -- https://www.district.in/events/parsec-jayanagar-by-param-2025-buy-tickets
    -- These are regular museum tickets
    -- not special events
    'PARAM FOUNDATION'
  );


DELETE FROM events
WHERE
  url IN (
    'https://together.buzz/event/test-ghofp8gg' -- Test event
    -- Music Camp is a very long event.
,
    'https://attagalatta.com/event_page.php?eventid=EVT1078'
-- The last date to apply is gone (25 May)
,   'https://map-india.org/map-events/training-course-in-conservation-of-photographs-in-museums-archives-and-collections/'
  );


-- Ideally,we would mark them using sameAs, but too much work for now
-- TODO: Pick up BMS/District Links using links in the event HTML 
-- at attagalatta.com event page, and then mark them using sameAs
DELETE FROM events
WHERE
  event_json ->> '$.location.name' LIKE '%Atta Galata%'
  AND url LIKE 'https://district.in%';


-- Low Quality events, and trips/treks from OdysseyVibes.in
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  event_json ->> '$.organizer.name' LIKE 'Odyssey vibes'
  -- https://urbanaut.app/about-hightable
  -- Currently rated 2.7 at Urbanaut
  -- Mostly stranger meets which are anyway meh.
  OR event_json ->> '$.organizer.name' LIKE 'HighTable'
  -- Stranger food meets rated 2.8
  OR event_json ->> '$.organizer.name' LIKE 'Bento Bento'
  -- Singles Mixers
  OR event_json ->> '$.organizer.name' LIKE 'Lobster Search'
  -- Low-quality Bangalore events or trips to outside BLR
  -- https://urbanaut.app/about-travel-trip-tourist
  OR event_json ->> '$.organizer.name' LIKE 'Travel Trip Tourist'
  -- Coworking is not events.
  OR event_json ->> 'name' LIKE '%Co-Working%'
  -- Advertisement for Rage Room Indiranagar
  OR url LIKE '%rage-room%'
  -- Social Mixers category on district
  OR (
    url like '%district.in%'
    and event_json  ->> '$.keywords' LIKE '%Social Mixers%'
  );


-- Mark some events as not happening in Bangalore
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'NOTINBLR')
  )
  -- Trips that technically start at KIAL airport
WHERE
  (
    event_json ->> '$.organizer.name' LIKE 'Sheena - Banjara%'
    OR event_json ->> '$.description' LIKE '%Karnataka Trekkers%'
    -- https://together.buzz/host/j-n-tulika-hdj, Yoga Retreats
    OR event_json ->> '$.performer.name' LIKE '%J N TULIKA%'
    OR url LIKE '%weekend-getaway%'
  ) OR (
    url like '%district.in%' AND 
      (
        event_json->>'$.keywords' LIKE '%camping%'
        OR event_json->>'$.keywords' LIKE '%trip%'
      )
  );


-- You cant attend a BIC Podcast
DELETE FROM events
WHERE
  event_json ->> '$.keywords' LIKE '%BIC%'
  AND event_json ->> '$.keywords' LIKE '%podcast%';


-- Woo-Woo https://rationalwiki.org/wiki/Woo
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'WOOWOO')
  )
WHERE
  (
    event_json ->> '$.name' LIKE '%QI Gong%'
    OR event_json ->> '$.name' LIKE '%tarot %'
    OR event_json ->> '$.name' LIKE '%Sound Immersion%'
    OR event_json ->> '$.name' LIKE '%sound bath%'
    OR event_json ->> '$.url'  LIKE '%sound-bath%'
    OR event_json ->> '$.name' LIKE '%sound healing%'
    OR event_json ->> '$.description' LIKE '%sound healing%'
    OR event_json ->> '$.description' LIKE '%pranic heal%'
    OR event_json ->> '$.description' LIKE '%aurabliss%'
    OR event_json ->> '$.name' LIKE '%Breathwork%'
    OR event_json ->> '$.name' LIKE '%SoundBath%'
    OR event_json ->> '$.name' LIKE '%ayurvedic workshop%'
    -- By tapping into your true voice, you have the ability to shift your reality
    OR event_json ->> '$.name' LIKE '%voice activation%'
    -- https://urbanaut.app/spot/akashic-records-workshop-june2025
    -- Messages from your guides and galactic family
    -- Insights into your soul’s themes, patterns, and past/future timelines
    -- Energetic healing and alignment as guided
    OR event_json ->> '$.organizer.name' LIKE '%sumedha purohit%'
    OR event_json ->> '$.description' LIKE '%cosmicsoulwhisperer%'
    -- Zuva Life
    OR event_json ->> '$.description' LIKE '%soul-led session%'
    -- https://urbanaut.app/partner/tarotwithtan
    OR event_json ->> '$.organizer.name' LIKE '%tarot with tan%'
    -- https://allevents.in/org/channel-ur-life-wellness-clinic/23383426
    OR event_json ->> '$.organizer.name' LIKE '%channel ur life%'
    -- They claim to treat Autism, Past Life Trauma, and much more. Ms. Rashmi
    -- Aiyappa perceives time and space very differently from that of a
    -- common man. She is a creator of a space that has an answer beyond
    -- religion, belief, faith, logic and philosophy – it is an experience .
    -- It is a science that the world has been waiting for. 
    -- Aashwasan is the only organization in the world
    -- that uses spiritual science tools and techniques
    -- such as Aura science and ESP to transform lives.
    OR event_json ->> '$.organizer.name' LIKE '%aashwasan foundation%'
    -- https://urbanaut.app/spot/soul-meridian
    OR event_json ->> '$.description' LIKE '%qi gong%'
    OR event_json ->> '$.description' LIKE '%crystal healing%'
    OR event_json ->> '$.name' LIKE '%soul meridian%'
    -- Not exactly woowoo, but I don't want to promote religious events either.
    OR event_json ->> '$.name' LIKE '%iskcon%'
    -- NOt exactly woowoo
    OR event_json ->> '$.organizer.name' LIKE '%ysmen international%'
    -- Breathwork, ice baths and "reset rituals"
    OR event_json ->> '$.organizer.name' LIKE '%soundsutraa%'
    OR event_json ->> '$.name' LIKE '%family constellation%'
  );


-- Religious bhajan sessions
DELETE FROM events
WHERE
  event_json ->> '$.name' LIKE '%bhajan%';


-- The Audacious Movement - WOOWOO
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'WOOWOO')
  )
WHERE
  lower(event_json ->> '$.organizer.name') IN (
    -- Very unclear what the events are about, except for "energy"
    'the audacious movement',
    -- New Acropolis is a cult ()
    'new acropolis'
  );


-- TODO: Mark high valued events
-- SELECT url, json_each.value->>'$.price' as price
-- 	FROM events, json_each(event_json->'$.offers')
-- 	WHERE CAST(json_each.value->>'$.price' AS INTEGER) >= 999;
-- Now Boarding Cafe is a boardgame venue
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'BOARDGAMES')
  )
WHERE
  event_json ->> '$.location.name' LIKE 'Now Boarding Cafe%';


-- All ReRoll hosted events, irrespective of venue
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'BOARDGAMES')
  )
WHERE
  url LIKE '%with-reroll%';


-- Mark treks and camping as NOTINBLR
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'NOTINBLR')
  )
WHERE
  (
    url LIKE '%-trek%'
    OR url LIKE '%camping%'
  )
  -- Sometimes called My Hikes India
  OR event_json ->> '$.organizer.name' LIKE 'my hikes%'
  OR event_json ->> '$.organizer.name' LIKE 'around big cities'
  OR event_json ->> '$.organizer.name' LIKE 'banbanjara travels llp'
  OR event_json ->> '$.organizer.name' LIKE 'dev balaji'
  -- Wonderla Amusement Park
  OR event_json ->> '$.organizer.name' LIKE '%wonderla%'
  -- Jollywood Adventure Park tickets
  OR event_json ->> '$.organizer.name' LIKE '%vels studios and entertainment%'
  -- Indiranagar Mini Golf Arena advertisements
  OR event_json ->> '$.organizer.name' LIKE 'mini golf madness llp'
  OR event_json ->> '$.organizer.name' LIKE '%escape2explore%'
  OR event_json ->> '$.organizer.name' LIKE 'namma trip'
  OR event_json ->> '$.organizer.name' LIKE '%tripper trails%'
  OR event_json ->> '$.organizer.name' LIKE '%tripbae%'
  OR event_json ->> '$.organizer.name' LIKE '%bolantur prabhu keerthan%'
  -- Around Big Cities treks list the organizer as a person
  OR event_json ->> '$.organizer.name' LIKE 'ameeshi goenka'
  OR event_json ->> '$.location.name' LIKE 'around big cities'
  OR event_json ->> '$.organizer.name' LIKE '%wanderon%'
  OR event_json ->> '$.organizer.name' LIKE 'thegreatbeyond.in'
  OR event_json ->> '$.name' LIKE '%trek%'
  OR event_json ->> '$.name' LIKE '%tour package%'
  OR event_json ->> '$.name' LIKE '%astro camp%'
  -- Multi-day trip packages that list a city pickup point as the venue
  OR event_json ->> '$.description' LIKE '%package amount%'
  OR event_json ->> '$.description' LIKE '%nights/days%'
  -- Wellness retreat on the outskirts
  OR event_json ->> '$.location.name' LIKE '%kshemavana%'

  -- All Travel events listed on HighApe
  OR (
    (
      event_json ->> '$.keywords' LIKE '%"travel"%'
      OR event_json ->> '$.keywords' LIKE '%"camping"%'
    )
    AND event_json ->> '$.keywords' LIKE '%"HIGHAPE"%'
  );


-- Music events listed on HIGHAPE that are
-- Free Entry are low-quality
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  event_json ->> '$.keywords' LIKE '%"highape"%'
  AND event_json ->> '$.keywords' LIKE '%"free entry"%'
  AND (
    event_json ->> '$.keywords' LIKE '%bollywood night%'
    OR event_json ->> '$.keywords' LIKE '%bollywood night%'
    OR event_json ->> '$.keywords' LIKE '%dj night%'
    OR event_json ->> '$.keywords' LIKE '%commercial music%'
    OR event_json ->> '$.keywords' LIKE '%karaoke night%'
  );

UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
-- Theme/Water/Snow parks
  url like '%district.in%' AND 
  (
    event_json->>'$.keywords' LIKE '%theme park%'
    OR event_json->>'$.keywords' LIKE '%snow park%'
    OR event_json->>'$.keywords' LIKE '%water park%'
    OR event_json->>'$.keywords' LIKE '%water park%'
    OR event_json->>'$.keywords' LIKE '%Game Zones%'
    OR event_json->>'$.keywords' LIKE '%Go Karting%'
    OR event_json->>'$.keywords' LIKE '%Arcades%'
    OR event_json->>'$.name' LIKE '%Agamer Game zone%'
    OR event_json->>'$.keywords' LIKE '%Escape Room%'
    OR event_json->>'$.keywords' LIKE '%Trampoline Parks%'
    OR event_json->>'$.keywords' LIKE '%Shooting Range%'
  );

-- MusicEvent is incorrectly used in many many allevents listings
UPDATE events
SET
  event_json = json_replace(event_json, '$.@type', 'Event')
WHERE
  url LIKE 'https://allevents.in%';


-- Tag Artzo Events as ARTZO from the domain artzo.in
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'ARTZO')
  )
WHERE
  url LIKE '%artzo.in%';


-- Real Estate events
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'BUSINESS')
  )
WHERE
  lower(event_json ->> '$.organizer.name') IN (
    -- Real Estate events
    'address advisors',
    -- Investment events
    'adamant ventures',
    -- education consulting
    'indian school of business',
    -- Investment events
    'invest in the usa (iiusa)',
     -- 🌟 India’s Premium Travel & Tourism Exhibition 🌟
    'india international travel mart',
    -- Real Estate events
    'hj real estates',
    -- education consulting
    'access mba',
    -- Business networking events
    'mohit sureka &amp; company',
    -- Orthodontic Conference
    '58th ioc bengaluru',
    -- Business networking events
    'trescon sd',
    -- Real Estate events
    'adrez advisors private limited',
    -- Photoshoots
    'arpit mudgal',
    -- Indian Travel Expo 2024
    'asian arab trade chamber of commerce',
    -- Property Expo
    'brandland advertising pvt ltd',
    -- Marketing business events
    'brightside online solutions',
    -- student business events
    'dtorr',
    -- education consulting
    'global tree careers private limited',
    'global tree',
    -- some confusingly described business events
    'mridu jhangiani',
    -- some investment learning events
    'walnut knowledge solutions private limited',
    -- indian startup events
    'z p enterprises',
    -- education consulting
    'upgrad abroad',
    -- Symposiums: https://allevents.in/org/charista-foundation/19674185
    'charista foundation',
    -- Educational long-workshops
    'etg career labs private limited',
    -- https://allevents.in/org/startup-synerz/25263240
    'startup synerz',
    -- https://startupparty.in/
    'startupparty',
    -- Some silly workshops
    'institute of product leadership (adaptive marketing solutions pvt ltd)',
    -- Laser Hair Reduction sessions are not events
    'reflection facethetics bengaluru',
    'seed global education',
    'etg career labs private limited',
    -- Startup meetups and pitches
    'cedat',
    -- Study abroad fairs
    'career gyan',
    -- Trade shows and summits
    'asia jewels show',
    'apparel resources pvt. ltd.',
    'intoaec',
    'world ai summit 2026',
    'happiest health systems private limited',
    -- Shopping exhibitions
    'maya bazaar',
    'brilarte media and marketing',
    'house of indiexpo',
    -- Finance, branding and founder sessions
    'stockgro',
    'creator chart',
    'business beyond usual - think & build hours'
  )
  OR lower(event_json ->> '$.organizer.name') LIKE '%exhibition%'
  OR event_json ->> '$.name' LIKE '%lifestyle exhibition%'
  OR event_json ->> '$.name' LIKE '%study abroad%'
  OR event_json ->> '$.name' LIKE '%education fair%'
  OR (
    -- Hustle Business Venue in HSR
    event_json ->> '$.location' LIKE '%hustlehub%'
    OR event_json ->> '$.location' LIKE '%karnataka trade promo%'
  )
  OR (
    -- Networking Meetups are BUSINESS events
    url LIKE '%network-meetup%'
    OR url LIKE '%networking-meetup%'
    OR url LIKE '%networking-meet%'
    OR url LIKE '%business-networking%'
    OR url LIKE '%virtual-hackathon%'
    OR url LIKE '%founders-investors%'
    OR url LIKE '%property-expo%'
    OR url LIKE '%property-expo%'
    OR url LIKE '%agentic-ai%'
    OR url LIKE '%ai-workshop%'
    OR url LIKE '%ai-master%'
    OR url LIKE '%entrepreneur-forum%'
    OR url LIKE '%-founders-%'
    OR url LIKE '%startups-club%'
    -- Allevents tags them as business events
    OR event_json ->> '$.keywords' LIKE 'business event'
    -- https://www.skillboxes.com/events?tagId=VjMrZ01TaHJGcHdnZU9MV1RldVpQdz09
    -- As well as District
    OR event_json ->> '$.keywords' LIKE '%Conference%'
    -- karnataka trade promotion organization 
    -- https://ktpo.karnataka.gov.in/english
    OR event_json ->> '$.keywords' LIKE '%KTPO%'
  );


-- organizer = Games Lab, title contains "Board" or "Mafia" or "Game Night", tag as BOARDGAMES
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'BOARDGAMES')
  )
WHERE
  event_json ->> '$.organizer.name' LIKE 'Games Lab'
  AND (
    event_json ->> '$.name' LIKE '%Board%'
    OR event_json ->> '$.name' LIKE '%Mafia%'
    OR event_json ->> '$.name' LIKE '%Game Night%'
  );

UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'UNDERLINE')
  )
WHERE
  event_json ->> '$.organizer.name' LIKE 'Underline Center'
  AND event_json->'$.keywords' NOT LIKE '%underline%'
;


-- if lower(event name) contains both "live screening" and "premier league", tag as SPORTS-SCREENING
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'SPORTS-SCREENING'
    )
  )
WHERE
  lower(event_json ->> '$.name') LIKE '%live screening%'
  AND lower(event_json ->> '$.name') LIKE '%premier league%';


UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.@type',
    'ScreeningEvent'
  )
WHERE
  
  event_json ->> '$.name' LIKE '%movie under the stars%'
  OR  event_json ->> '$.name' LIKE '%sunset cinema%';



-- Do the same as above but use IPL team names
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'SPORTS-SCREENING'
    )
  )
WHERE
  (
    event_json ->> '$.name' LIKE '%live cricket screening%'
    OR event_json ->> '$.name' LIKE '%live ipl%'
    OR event_json ->> '$.name' LIKE '%ipl live%'
    OR event_json ->> '$.name' LIKE '%ipl screening%'
    OR event_json ->> '$.keywords' LIKE '%ipl screening%'
    -- This is highape specific but works as long as we club it with sports
    -- It still catches some bollywood nights, but those are anyway marked as LOW QUALITY
    OR (event_json ->> '$.keywords' LIKE '%live session & streaming%' AND event_json ->> '$.keywords' LIKE '%sports%')
    OR event_json ->> '$.name' LIKE '%live cricket screening%'
    OR (event_json ->> '$.keywords' LIKE '%screening%' AND event_json->>'$.description' LIKE '%IPL%')
  );
-- Do the same as above but use F1 Screening tags and GRAND PRIX names
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'SPORTS-SCREENING'
    )
  )
WHERE
  (
    event_json ->> '$.name' LIKE '%f1 live%'
    OR event_json ->> '$.name' LIKE '%f1 screening%'
    OR event_json ->> '$.name' LIKE '%formula 1 live%'
    OR event_json ->> '$.name' LIKE '%formula 1 screening%'
    OR event_json ->> '$.keywords' LIKE '%f1 screening%'
    OR event_json ->> '$.keywords' LIKE '%grand prix%'
    OR event_json ->> '$.keywords' LIKE '%screening of f1%'
    OR event_json ->> '$.keywords' LIKE '%screening of formula 1%'
    OR event_json ->> '$.keywords' LIKE '%screening of formula1%'
  ) 
  -- We want to make sure that other F1 events are not included
  AND event_json LIKE '%screening%';


-- Too Many Dandiya events, so we tag them out.
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'DANDIYA')
  )
WHERE
  event_json LIKE '%dandiya%';


-- Low Quality drinking focused events
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  event_json ->> '$.description' LIKE '%get sloshed%'
  OR event_json ->> '$.description' LIKE '%magic mocktails%'
  OR event_json ->> '$.keywords' LIKE '%tipsy%'
  -- The Venue has very bad reviews on Google Maps
  -- Even for their flagship shows
  -- https://maps.app.goo.gl/QHP67KA728ucAysj7
  OR event_json ->> '$.location' LIKE '%ignite super club%'
  -- Low Quality events: https://allevents.in/org/bengaluru-pub-crawlers/25174916#
  OR event_json ->> '$.organizer.name' LIKE '%bengaluru pub crawlers%'
  ;


-- Regular Clubbing nights are not noteworthy events
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  event_json ->> '$.name' LIKE '%ladies night%'
  OR event_json ->> '$.keywords' LIKE '%ladies night%'
  OR event_json ->> '$.description' LIKE '%ladies night%'
  OR event_json ->> '$.description' LIKE '%dj night%'
  -- Secret Story Indiranagar
  OR event_json ->> '$.description' LIKE '%ladies & models night%'
  OR event_json ->> '$.name' LIKE '%ladies thursday%'
  OR event_json ->> '$.description' LIKE '%bolly tech night%'
  OR event_json ->> '$.description' LIKE '%wild west friday%'
  OR event_json ->> '$.description' LIKE '%punjabi night%'
  OR event_json ->> '$.name' LIKE '%rock bottom monday%'
  OR event_json ->> '$.name' LIKE '%bollywood night%'
  OR event_json ->> '$.keywords' LIKE '%bollywood night%'
  OR event_json ->> '$.keywords' LIKE '%techno%'
  OR event_json ->> '$.name' LIKE '%bollywood bash%'
  OR event_json ->> '$.name' LIKE '%monsoon monday%'
  OR event_json ->> '$.name' LIKE '%pub crawl%'
  OR event_json ->> '$.name' LIKE '%episode monday%'
  OR event_json ->> '$.name' LIKE '%worth it monday%'
  OR event_json ->> '$.name' LIKE '%tashan tuesday%'
  OR event_json ->> '$.name' LIKE '%tashn tuesday%'
  OR event_json ->> '$.name' LIKE '%tease tuesday%'
  OR event_json ->> '$.name' LIKE '%mix bag wednesday%'
  OR event_json ->> '$.name' LIKE '%mixbag wednesday%'
  OR event_json ->> '$.name' LIKE '%tgif friday%'
  OR event_json ->> '$.name' LIKE '%navrang navratri%'
  OR event_json ->> '$.name' LIKE '%techno terrace%' -- indigo xp
  OR event_json ->> '$.name' LIKE '%athyachari monday%'
  OR event_json ->> '$.organizer.name' LIKE 'vro hospitality' -- highape music nights
  OR event_json ->> '$.organizer.name' LIKE 'avikk hospitality llp'
  OR event_json ->> '$.organizer.name' LIKE '%vnh events%'
  OR event_json ->> '$.organizer.name' LIKE '%miami entertainment%'
  OR event_json ->> '$.organizer.name' LIKE '%sd events%'
  OR event_json ->> '$.keywords' LIKE '%vro hospitality%'
  OR event_json ->> '$.keywords' LIKE '%OIEPL%' -- Gold Rush Brews
  -- Gaming Arcade ticket sales are not events
  OR event_json ->> '$.keywords' LIKE '%The Grid - Gaming Arena%'
  OR event_json ->> '$.keywords' LIKE '%The Grid-Bowling%'
  OR event_json ->> '$.organizer.name' LIKE 'hex entertainment llp' -- Also The Grid
  OR event_json LIKE '%deck-gigs%' -- SkyDeck gigs
  -- Stranger Meets
  OR event_json ->> '$.organizer.name' LIKE 'caridia official'
  OR url LIKE '%tuesday-lets-party%'
  OR url LIKE '%dinner-with-strangers%'
  OR event_json->>'$.organizer.name' LIKE 'VOYAGIO' -- Urbanaut Stranger meets
  -- Club and DJ night promoters, mostly on HighApe
  OR lower(event_json ->> '$.organizer.name') IN (
    'toca', 'toca brigade', 'nighthype entertainments', 'atabb apromotions',
    'rajata hospitality llp', 'urban ns events', 'brick & brew', 'hoot growth',
    'hoot craftwork 2.0', 'sky high entertainment', 'namma vibes',
    'jayasimha events', 'weapon entertainment', 'nitecrush events',
    'shane events', 'bollybox events', 'dj guroove', 'aqua fire events',
    'richboyz', 'hyp3 nightclub', 'gulp - pub | bar | restaurant',
    'hello foodie', 'meghraj entertainment', 'centigrade india', 'reboot the pub'
  )
  -- Club venues
  OR event_json ->> '$.location.name' LIKE '%budbee%'
  OR event_json ->> '$.location.name' LIKE '%sugar factory%'
  OR event_json ->> '$.location.name' LIKE '%badmaash%'
  OR event_json ->> '$.location.name' LIKE '%hyp3%'
  OR event_json ->> '$.location.name' LIKE '%hydra club%'
  OR event_json ->> '$.location.name' LIKE '%house of dopamine%'
  OR event_json ->> '$.location.name' LIKE '%sunburn union%'
  OR event_json ->> '$.name' LIKE '%ft dj%'
  OR event_json ->> '$.name' LIKE '%ft. dj%'
  OR event_json ->> '$.name' LIKE 'dj %'
  OR event_json ->> '$.name' LIKE '%dj night%'
  OR event_json ->> '$.name' LIKE '%dj party%'
  OR event_json ->> '$.name' LIKE '%karaoke%'
  OR event_json ->> '$.name' LIKE '%theme night%'
  OR event_json ->> '$.name' LIKE '%theme party%'
  OR event_json ->> '$.name' LIKE '%tamil night%'
  OR event_json ->> '$.name' LIKE '%bollytech%'
  OR event_json ->> '$.name' LIKE '%bollyholly%'
  OR event_json ->> '$.name' LIKE '%bhangra rave%'
  OR event_json ->> '$.name' LIKE '%tipsy%'
  OR event_json ->> '$.name' LIKE '%ladies%night%'
  OR event_json ->> '$.name' LIKE '%sherlock nights%'
;


-- Mixers, venue ads and restaurant/pub promotions
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  event_json ->> '$.name' LIKE '%social mixer%'
  OR event_json ->> '$.name' LIKE '%social meetup%'
  OR event_json ->> '$.name' LIKE '%travellers meetup%'
  OR event_json ->> '$.name' LIKE '%sunday social%'
  OR event_json ->> '$.name' LIKE '%sundown socials%'
  OR event_json ->> '$.name' LIKE '%pitch & pair%'
  -- Venue and activity ads, not events
  OR lower(event_json ->> '$.organizer.name') IN ('play arena', 'kanto aerosports')
  OR event_json ->> '$.name' LIKE '%rage therapy%'
  OR event_json ->> '$.name' LIKE '%photo shoot%'
  OR event_json ->> '$.name' LIKE '%photoshoot%'
  OR event_json ->> '$.name' LIKE '%klaydate%'
  -- Pub and restaurant promotions
  OR event_json ->> '$.name' LIKE '%oktoberfest%'
  OR event_json ->> '$.name' LIKE '%milltober%'
  OR event_json ->> '$.name' LIKE '%raise a stein%'
  OR event_json ->> '$.name' LIKE '%cake buffet%'
  OR lower(event_json ->> '$.organizer.name') = 'old mill brewing co.'
  OR event_json ->> '$.location.name' LIKE '%doubletree by hilton%'
  OR event_json ->> '$.location.name' LIKE '1882 restaurant%'
;


-- Secret Story music nights
-- THRIFTY-X is a shady event organizer
-- Stranger Meets are events, but meh https://district.in/search?q=Thrifty
-- They also host dance workshops in fast food places :/
-- And double book events at the same venue to get more visibility
-- https://district.in/thrifty-x-bachata-bangalore-sep29-2024/event
-- https://district.in/thrifty-x-salsa-bangalore-sep29-2024/event
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  url LIKE '%thrifty-x-%'
  OR event_json ->> '$.organizer.name' LIKE '%Event Navigator%'
  OR event_json ->> '$.organizer.name' LIKE '%Bubblegum Circle%';

UPDATE events SET 
  event_json = json_replace(
    event_json,
    '$.@type',
    'LiteraryEvent'
  )
WHERE
  event_json ->> '$.name' LIKE '%dialogues with books%'
  OR event_json ->> '$.name' LIKE '%Broke Bibliophiles%';



-- I host Puzzled Pint BLR, and it is a 100% certified quality event.
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'CURATED')
  )
WHERE
  url LIKE '%puzzled-pint-bangalore%';


-- Tag location as HSR
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'HSR')
  )
WHERE
  event_json LIKE '%HSR%';


UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'KORAMANGALA'
    )
  )
WHERE
  event_json LIKE '%koramangala%';


-- We combine Domlur and Indiranagar
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'INDIRANAGAR'
    )
  )
WHERE
  (
    event_json LIKE '%domlur%'
    OR event_json LIKE '%indiranagar%'
    OR event_json LIKE '%old airport road%'
  );


UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'JAYANAGAR')
  )
WHERE
-- Avoid matching Vijayanagar
  event_json LIKE '% jayanagar%';


UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'JPNAGAR')
  )
WHERE
  event_json ->> '$.location' LIKE '%jp nagar%'
  OR event_json ->> '$.location' LIKE '%j p nagar%'
  OR event_json ->> '$.location' LIKE '%j. p. nagar%'
  OR event_json ->> '$.location' LIKE '%j. p nagar%'
  OR event_json ->> '$.location' LIKE '%j.p nagar%';


-- Merge Brookefield with whitefield for now
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'WHITEFIELD')
  )
WHERE
  event_json ->> '$.location' LIKE '%whitefield%'
  OR event_json ->> '$.location' LIKE '%brookefield%';


UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'JAKKUR')
  )
WHERE
  event_json ->> '$.location' LIKE '%jakkur%';


UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'HEBBAL')
  )
WHERE
  event_json ->> '$.location' LIKE '%HEBBAL%';


-- CBD
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'CBD')
  )
WHERE
  (
    event_json ->> '$.location' LIKE '%1 mg%'
    OR event_json ->> '$.location' LIKE '%mg road%'
    OR event_json ->> '$.location' LIKE '%residency road%'
    OR event_json ->> '$.location' LIKE '%residency rd%'
    OR event_json ->> '$.location' LIKE '%mahatma gandhi road%'
    OR event_json ->> '$.location' LIKE '%jayamahal%'
    OR event_json ->> '$.location' LIKE '%ashok nagar%'
    OR event_json ->> '$.location' LIKE '%churchstreet%'
    OR event_json ->> '$.location' LIKE '%church street%'
    OR event_json ->> '$.location' LIKE '%cubbon park%'
    OR event_json ->> '$.location' LIKE '%church st%'
    OR event_json ->> '$.location' LIKE '%lavelle road%'
    OR event_json ->> '$.location' LIKE '%lavelle rd%'
    OR event_json ->> '$.location' LIKE '%museum road%'
    OR event_json ->> '$.location' LIKE '%museum rd%'
    OR event_json ->> '$.location' LIKE '%ashok nagar%'
    OR event_json ->> '$.location' LIKE '%shivaji nagar%'
    OR event_json ->> '$.location' LIKE '%st mark''s road%'
    OR event_json ->> '$.location' LIKE '%st mark road%'
    OR event_json ->> '$.location' LIKE '%st.mark road%'
    OR event_json ->> '$.location' LIKE '%st.mark''s road%'
    OR event_json ->> '$.location' LIKE '%shanthala nagar%'
    -- The university has multiple colleges and campuses
    -- But most are near or within CBD
    OR event_json ->> '$.location' LIKE '%st. joseph''s%'
  );


-- Electronic City
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'ECITY')
  )
WHERE
  (
    event_json ->> '$.location' LIKE '%electronic city%'
    OR event_json ->> '$.location' LIKE '%e-city%'
    OR event_json ->> '$.location' LIKE '%electroniccity%'
    OR event_json ->> '$.location' LIKE '%electronic-city%'
  );


-- Multi-day BSF events are marked as BSF/MULTIDAY
-- so they can be excluded in the curated calendar.
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'BSF/MULTIDAY'
    )
  )
WHERE
  event_json ->> '$.keywords' LIKE '%BSF%'
  AND substr(event_json ->> '$.startDate', 0, 10) != substr(event_json ->> '$.endDate', 0, 10);


-- Comedy Theater makes duplicate listings for their events
-- That are multiple days long.
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'LOW-QUALITY'
    )
  )
WHERE
  (
    event_json ->> '$.location' LIKE '%comedy theater%'
    -- LVDS multi-day events are courses
    OR event_json ->> '$.location' LIKE '%LVDS%'
    OR url LIKE '%garba-course%'
  )
  AND substr(event_json ->> '$.startDate', 0, 10) != substr(event_json ->> '$.endDate', 0, 10);

-- Mark events where the description includes the words
-- "online session" or "zoom link" as ONLINE
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'ONLINE'
    )
  )
WHERE
 event_json ->> '$.description' LIKE '%online session%'
 OR event_json ->> '$.description' LIKE '%zoom link%';

-- Everything with a urbanaut.app url and TPCC in capital in the title
-- should be tagged as TPCC
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(
      event_json -> '$.keywords',
      '$[#]',
      'TPCC'
    )
  )
WHERE
  url LIKE '%urbanaut.app%'
  AND event_json ->> '$.name' LIKE '%TPCC%';

-- For events tagged as TPCC, if the description contains "screening", we can change 
-- event type to ScreeningEvent
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.@type',
    'ScreeningEvent'
  )
WHERE
  event_json ->> '$.keywords' LIKE '%TPCC%'
  AND event_json ->> '$.description' LIKE '%screening%';

DELETE FROM events WHERE event_json->> '$.location' LIKE '%andhra pradesh%';


-- Update location details for The Humming Tree
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.location.address',
    '763, 100 Feet Rd, HAL 2nd Stage, Appareddipalya, Indiranagar, Bengaluru, Karnataka 560008, India',
    '$.location.geo',
    json('{"@type": "GeoCoordinates", "latitude": 12.9711533, "longitude": 77.6409725}')
  )
WHERE
  lower(event_json ->> '$.location.name') = 'the humming tree'
  OR lower(event_json ->> '$.organizer.name') = 'the humming tree';


-- Mark events in other major Indian cities as NOTINBLR
UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'NOTINBLR')
  )
WHERE
  event_json -> '$.keywords' NOT LIKE '%NOTINBLR%'
  AND (
    event_json ->> '$.location' LIKE '%Mumbai%'
    OR event_json ->> '$.location' LIKE '%Delhi%'
    OR event_json ->> '$.location' LIKE '%Hyderabad%'
    OR event_json ->> '$.location' LIKE '%Ahmedabad%'
    OR event_json ->> '$.location' LIKE '%Chennai%'
    OR event_json ->> '$.location' LIKE '%Kolkata%'
    OR event_json ->> '$.location' LIKE '%Surat%'
    OR event_json ->> '$.location' LIKE '%Pune%'
    OR event_json ->> '$.location' LIKE '%Jaipur%'
    OR event_json ->> '$.location' LIKE '%Lucknow%'
    OR event_json ->> '$.location' LIKE '%Kanpur%'
    OR event_json ->> '$.location' LIKE '%Nagpur%'
    OR event_json ->> '$.location' LIKE '%Indore%'
    OR event_json ->> '$.location' LIKE '%Thane%'
    OR event_json ->> '$.location' LIKE '%Bhopal%'
    OR event_json ->> '$.location' LIKE '%Visakhapatnam%'
    OR event_json ->> '$.location' LIKE '%Patna%'
    OR event_json ->> '$.location' LIKE '%Vadodara%'
    OR event_json ->> '$.location' LIKE '%Ghaziabad%'
    OR event_json ->> '$.location' LIKE '%Ludhiana%'
    OR event_json ->> '$.location' LIKE '%Agra%'
    OR event_json ->> '$.location' LIKE '%Nashik%'
    OR event_json ->> '$.location' LIKE '%Faridabad%'
    OR event_json ->> '$.location' LIKE '%Meerut%'
    OR event_json ->> '$.location' LIKE '%Rajkot%'
    OR event_json ->> '$.location' LIKE '%Varanasi%'
    OR event_json ->> '$.location' LIKE '%Srinagar%'
    OR event_json ->> '$.location' LIKE '%Aurangabad%'
    OR event_json ->> '$.location' LIKE '%Dhanbad%'
    OR event_json ->> '$.location' LIKE '%Amritsar%'
    OR event_json ->> '$.location' LIKE '%Prayagraj%'
    OR event_json ->> '$.location' LIKE '%Howrah%'
    OR event_json ->> '$.location' LIKE '%Ranchi%'
    OR event_json ->> '$.location' LIKE '%Jabalpur%'
    OR event_json ->> '$.location' LIKE '%Gwalior%'
    OR event_json ->> '$.location' LIKE '%Coimbatore%'
    OR event_json ->> '$.location' LIKE '%Vijayawada%'
    OR event_json ->> '$.location' LIKE '%Jodhpur%'
    OR event_json ->> '$.location' LIKE '%Madurai%'
    OR event_json ->> '$.location' LIKE '%Raipur%'
    OR event_json ->> '$.location' LIKE '%Kota%'
    OR event_json ->> '$.location' LIKE '%Bareilly%'
  );
