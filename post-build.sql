-- Description: This script is executed before the build of the database
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
  -- HighApe event listings do not include the organizer field 
  -- But we pick it up from meta tags into keywords
  OR event_json ->> '$.keywords' LIKE '%small world%'
  OR event_json ->> '$.organizer.name' LIKE '%urban solace%'
  -- Silly dating events: https://insider.in/free-speed-dating-events-in-bengaluru-sep7-2024/event
  OR event_json ->> '$.organizer.name' LIKE '%your dream partner%'
  -- Silly dating events on insider
  OR event_json ->> '$.organizer.name' LIKE '%vinit kotadiya%'
  -- Silly dating event organizer: https://insider.in/search?q=Rashid%20Mubarak%20Nadaf
  OR event_json ->> '$.organizer.name' LIKE '%rashid mubarak nadaf%';


-- BIC lists their events on Insider, but we have their original calendar
-- BCC lists their events on Insider, but we have their original calendar
DELETE FROM events
WHERE
  lower(event_json ->> '$.organizer.name') IN (
    'bangalore international centre',
    'tarun rajendra mittal (bangalore chess club)'
  );


DELETE FROM events
WHERE
  url IN (
    'https://insider.in/isl-2024-25-bengaluru-fc-membership-season-12/event' -- Memberships are not events
,
    'https://together.buzz/event/test-ghofp8gg' -- Test event
    -- Music Camp is a very long event.
,
    'https://attagalatta.com/event_page.php?eventid=EVT1078'
  );


-- Ideally,we would mark them using sameAs, but too much work for now
-- TODO: Pick up BMS/Insider Links using links in the event HTML 
-- at attagalatta.com event page, and then mark them using sameAs
DELETE FROM events
WHERE
  event_json ->> '$.location.name' LIKE '%Atta Galata%'
  AND url LIKE 'https://insider.in%';


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
  event_json ->> '$.organizer.name' = 'Odyssey vibes';


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
    OR
    -- https://together.buzz/host/j-n-tulika-hdj, Yoga Retreats
    event_json ->> '$.performer.name' LIKE '%J N TULIKA%'
    OR url LIKE '%weekend-getaway%'
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
    OR event_json ->> '$.name' LIKE '%Breathwork%'
    OR event_json ->> '$.name' LIKE '%SoundBath%'
    -- By tapping into your true voice, you have the ability to shift your reality
    OR event_json ->> '$.name' LIKE '%voice activation%'
    -- https://urbanaut.app/spot/akashic-records-workshop-june2025
    -- Messages from your guides and galactic family
    -- Insights into your soul’s themes, patterns, and past/future timelines
    -- Energetic healing and alignment as guided
    OR event_json ->> '$.organizer.name' LIKE '%sumedha purohit%'
    OR event_json ->> '$.description' LIKE '%cosmicsoulwhisperer%'
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
  );


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
  OR event_json ->> '$.organizer.name' LIKE 'manoj t s - escape2explore adventures'
  OR event_json ->> '$.organizer.name' LIKE 'namma trip'
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
    OR event_json ->> '$.keywords' LIKE '%karaoke night%'
    OR event_json ->> '$.keywords' LIKE '%vro hospitality%'
    OR event_json ->> '$.keywords' LIKE '%OIEPL%' -- Gold Rush Brews
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
    'charista foundation'
  )
  OR (
    -- Hustle Business Venue in HSR
    event_json ->> '$.location' LIKE '%hustlehub%'
  )
  OR (
    -- Networking Meetups are BUSINESS events
    url LIKE '%network-meetup%'
    OR url LIKE '%networking-meetup%'
    OR url LIKE '%virtual-hackathon%'
    OR url LIKE '%founders-investors%'
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
  event_json ->> '$.organizer.name' = 'Games Lab'
  AND (
    event_json ->> '$.name' LIKE '%Board%'
    OR event_json ->> '$.name' LIKE '%Mafia%'
    OR event_json ->> '$.name' LIKE '%Game Night%'
  );


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
  );


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
  OR event_json ->> '$.keywords' LIKE '%tipsy%';


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
  OR event_json ->> '$.name' LIKE '%rock bottom monday%'
  OR event_json ->> '$.name' LIKE '%bollywood night%'
  OR event_json ->> '$.keywords' LIKE '%bollywood night%'
  OR event_json ->> '$.name' LIKE '%bollywood bash%'
  OR event_json ->> '$.name' LIKE '%monsoon monday%'
  OR event_json ->> '$.name' LIKE '%pub crawl%'
  OR event_json ->> '$.name' LIKE '%episode monday%'
  OR event_json ->> '$.name' LIKE '%worth it monday%'
  OR event_json ->> '$.name' LIKE '%tashan tuesday%'
  OR event_json ->> '$.name' LIKE '%tashn tuesday%'
  OR event_json ->> '$.name' LIKE '%tgif friday%'
  OR event_json ->> '$.name' LIKE '%navrang navratri%'
  OR event_json ->> '$.name' LIKE '%techno terrace%' -- indigo xp
  OR event_json ->> '$.name' LIKE '%athyachari monday%'
  OR event_json ->> '$.organizer.name' LIKE 'VRO Hospitality' -- highape music nights
  OR event_json ->> '$.organizer.name' LIKE 'avikk hospitality llp';


-- Secret Story music nights
-- THRIFTY-X is a shady event organizer
-- Stranger Meets are events, but meh https://insider.in/search?q=Thrifty
-- They also host dance workshops in fast food places :/
-- And double book events at the same venue to get more visibility
-- https://insider.in/thrifty-x-bachata-bangalore-sep29-2024/event
-- https://insider.in/thrifty-x-salsa-bangalore-sep29-2024/event
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
  event_json LIKE '%domlur%'
  OR event_json LIKE '%jayanagar%';


UPDATE events
SET
  event_json = json_replace(
    event_json,
    '$.keywords',
    json_insert(event_json -> '$.keywords', '$[#]', 'JPNAGAR')
  )
WHERE
  event_json ->> '$.location' LIKE '%jp nagar%'
  OR event_json ->> '$.location' LIKE '%j p nagar%';


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
    OR event_json ->> '$.location' LIKE '%Museum Road%'
    OR event_json ->> '$.location' LIKE '%Museum rd%'
    OR event_json ->> '$.location' LIKE '%Ashok Nagar%'
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
  )
  AND substr(event_json ->> '$.startDate', 0, 10) != substr(event_json ->> '$.endDate', 0, 10);
