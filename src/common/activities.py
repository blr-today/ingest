# Bump VERSION whenever a tag or question changes, so cached answers are asked again
VERSION = 8

# Watching, listening or tasting, versus doing it yourself
WATCH, DO = "experiential", "participatory"

# tag: (mode, question asked of every event); a slash names the parent, and
# parents without a question only group their children
TAGS = {
    "ART-CRAFT": (
        DO,
        "At this event, do attendees make an artwork or craft object themselves?",
    ),
    "ART-CRAFT/PAINTING": (
        DO,
        "Is painting, drawing or sketching the main activity at this event, such as sip-and-paint or a canvas painting workshop?",
    ),
    "ART-CRAFT/CALLIGRAPHY": (
        DO,
        "Is this event about calligraphy, hand lettering or typography?",
    ),
    "ART-CRAFT/PRINTMAKING": (
        DO,
        "Is this event about printmaking, such as linocut, block printing, woodcut or cyanotype?",
    ),
    "ART-CRAFT/POTTERY": (
        DO,
        "At this event, do attendees work with clay, such as wheel pottery, hand-building or clay modelling?",
    ),
    "ART-CRAFT/RESIN": (DO, "At this event, do attendees make resin or epoxy art?"),
    "ART-CRAFT/KINTSUGI": (
        DO,
        "Is this event about kintsugi, the Japanese art of mending pottery with gold?",
    ),
    "ART-CRAFT/CANDLES": (DO, "At this event, do attendees make candles?"),
    "ART-CRAFT/JEWELLERY": (
        DO,
        "At this event, do attendees make wearable jewellery such as earrings, necklaces or bracelets?",
    ),
    "ART-CRAFT/PERFUMERY": (
        DO,
        "At this event, do attendees make perfume, soap or skincare products?",
    ),
    "ART-CRAFT/PLANTS": (
        DO,
        "Is this event about terrariums, gardening, plants or flower arranging?",
    ),
    "EXHIBITION": (
        WATCH,
        "Is this event an art, photography or design exhibition for visitors to view?",
    ),
    "PHOTOGRAPHY": (
        DO,
        "At this event, do attendees take photographs, such as on a photo walk or in a photography class?",
    ),
    "FILMMAKING": (
        DO,
        "At this event, do attendees learn filmmaking, animation or video making?",
    ),
    "SHOW": (WATCH, None),
    "SHOW/THEATER": (
        WATCH,
        "Is this event a theatre play, drama or puppetry performance for an audience?",
    ),
    "SHOW/DANCE": (
        WATCH,
        "Is this event a dance performance for an audience, such as contemporary or classical Indian dance?",
    ),
    "SHOW/STANDUP": (WATCH, "Is this event a stand-up comedy show?"),
    "SHOW/IMPROV": (
        WATCH,
        "Is this event an improv comedy or improvised theatre show for an audience?",
    ),
    "SHOW/MAGIC": (WATCH, "Is this event a magic or mentalism show?"),
    "SHOW/STORYTELLING": (
        WATCH,
        "Is this event a storytelling session, such as folk tales or personal stories told aloud, rather than stand-up comedy?",
    ),
    "SHOW/POETRY": (
        WATCH,
        "Is this event a poetry reading or recital, where poets perform for an audience?",
    ),
    "SHOW/PERFORMANCE-ART": (
        WATCH,
        "Is this event an experimental or multidisciplinary performance mixing movement, video, music or spoken word?",
    ),
    "ON-STAGE": (DO, None),
    "ON-STAGE/OPEN-MIC": (
        DO,
        "Is this event an open mic where attendees can sign up to perform?",
    ),
    "ON-STAGE/ACTING": (
        DO,
        "At this event, do attendees act themselves, such as in a theatre or acting workshop?",
    ),
    "ON-STAGE/IMPROV": (
        DO,
        "At this event, do attendees do improv themselves, such as in an improv class or jam?",
    ),
    "LIVE-MUSIC": (
        WATCH,
        "Is live music by musicians or a band the main attraction of this event?",
    ),
    "LIVE-MUSIC/INDIAN-CLASSICAL": (
        WATCH,
        "Is this event a Carnatic or Hindustani classical music performance?",
    ),
    "LIVE-MUSIC/JAZZ": (WATCH, "Is this event a jazz performance?"),
    "LIVE-MUSIC/ROCK-METAL": (
        WATCH,
        "Is this event a gig by a rock, metal or punk band?",
    ),
    "LIVE-MUSIC/SUFI-QAWWALI": (
        WATCH,
        "Is this event a sufi, qawwali or ghazal performance?",
    ),
    "LIVE-MUSIC/FOLK": (WATCH, "Is this event a performance of folk music?"),
    "LIVE-MUSIC/DEVOTIONAL": (
        WATCH,
        "Is devotion the main purpose of this event, like a kirtan, bhajan, satsang or chanting "
        "session, rather than a concert of music with devotional roots, like qawwali?",
    ),
    "LISTENING-SESSION": (
        WATCH,
        "Is this event an album or vinyl listening session?",
    ),
    "MUSIC-MAKING": (DO, None),
    "MUSIC-MAKING/JAM": (
        DO,
        "Is this event a music jam, sing-along or choir where attendees make music together?",
    ),
    "MUSIC-MAKING/LESSON": (
        DO,
        "Is this event a class to learn an instrument or singing?",
    ),
    "NIGHTLIFE": (None, None),
    "NIGHTLIFE/DJ": (None, "Is this event a DJ set, club night or party?"),
    "NIGHTLIFE/BOLLYWOOD": (
        None,
        "Is this event a DJ night or party that plays Bollywood or other Indian film music?",
    ),
    "NIGHTLIFE/KARAOKE": (None, "Is this event a karaoke night?"),
    "MOVIE-SCREENING": (WATCH, "Is a film or documentary screened at this event?"),
    "SPORTS-SCREENING": (
        WATCH,
        "Is this event a screening of a live sports broadcast for people to watch together?",
    ),
    "SPORTS-SCREENING/F1": (
        WATCH,
        "Is this event a screening of a Formula 1 Grand Prix broadcast?",
    ),
    "SPORTS-SCREENING/FOOTBALL": (
        WATCH,
        "Is this event a screening of a football match broadcast?",
    ),
    "SPORTS-SCREENING/CRICKET": (
        WATCH,
        "Is this event a screening of a cricket match broadcast, such as an IPL or international match?",
    ),
    "LIVE-SPORTS": (
        WATCH,
        "At this event, do attendees watch a live sports match or fight in the stadium or arena?",
    ),
    "GAMES": (DO, None),
    "GAMES/BOARDGAMES": (
        DO,
        "At this event, do attendees play board games, card games or tabletop games?",
    ),
    "GAMES/SOCIAL-DEDUCTION": (
        DO,
        "At this event, do attendees play social deduction games such as Mafia, Werewolf or Blood on the Clocktower?",
    ),
    "GAMES/TTRPG": (
        DO,
        "At this event, do attendees play tabletop role-playing games such as Dungeons & Dragons?",
    ),
    "GAMES/CHESS": (DO, "Is this event about chess?"),
    "GAMES/QUIZ": (DO, "Is this event a quiz or trivia night?"),
    "GAMES/PUZZLES": (
        DO,
        "At this event, do attendees solve jigsaws, crosswords, Rubik's cubes or other puzzles?",
    ),
    "FITNESS": (
        DO,
        "Is this event a workout, sport or fitness session for attendees?",
    ),
    "FITNESS/RUNNING": (
        DO,
        "At this event, do attendees go running, such as a run club, fun run or marathon?",
    ),
    "FITNESS/CYCLING": (
        DO,
        "At this event, do attendees cycle, such as a group ride?",
    ),
    "FITNESS/YOGA": (DO, "Is this event a yoga session?"),
    "FITNESS/PILATES": (DO, "Is this event a pilates session?"),
    "FITNESS/MARTIAL-ARTS": (
        DO,
        "Is this event martial arts, boxing or self-defence training?",
    ),
    "FITNESS/CLIMBING": (
        DO,
        "At this event, do attendees climb, such as bouldering or wall climbing?",
    ),
    "FITNESS/RACKET-SPORTS": (
        DO,
        "At this event, do attendees play badminton, pickleball, padel, squash or tennis?",
    ),
    "FITNESS/TEAM-SPORTS": (
        DO,
        "At this event, do attendees play football, basketball, cricket or another team sport?",
    ),
    "DANCING": (
        DO,
        "At this event, do attendees dance themselves, such as a dance class or social dance night?",
    ),
    "DANCING/LATIN": (
        DO,
        "At this event, do attendees dance salsa, bachata, kizomba or another Latin dance?",
    ),
    "DANCING/SWING-BALLROOM": (
        DO,
        "At this event, do attendees dance swing, lindy hop, tango, waltz or another ballroom dance?",
    ),
    "DANCING/BOLLYWOOD": (
        DO,
        "At this event, do attendees learn or dance Bollywood choreography?",
    ),
    "DANCING/HIPHOP": (
        DO,
        "At this event, do attendees dance hip-hop, street dance or K-pop choreography?",
    ),
    "DANCING/CONTEMPORARY": (
        DO,
        "At this event, do attendees dance contemporary, jazz dance or ballet?",
    ),
    "DANCING/INDIAN-CLASSICAL": (
        DO,
        "At this event, do attendees learn Bharatanatyam, Kathak or another Indian classical dance?",
    ),
    "DANCING/GARBA": (DO, "At this event, do attendees dance garba or dandiya?"),
    "OUTDOORS": (DO, None),
    "OUTDOORS/ADVENTURE": (
        DO,
        "Is this event an adventure activity such as karting, paintball, kayaking, horse riding or shooting?",
    ),
    "OUTDOORS/HERITAGE-WALK": (
        DO,
        "Is this event a heritage, history or city walk or tour?",
    ),
    "OUTDOORS/NATURE-WALK": (
        DO,
        "Is this event a guided walk in nature, such as a tree, butterfly or lake walk?",
    ),
    "OUTDOORS/BIRDING": (DO, "Is this event birdwatching?"),
    "OUTDOORS/TREK": (DO, "Is this event a trek or hike?"),
    "OUTDOORS/STARGAZING": (DO, "Is this event about stargazing or astronomy?"),
    "TASTING": (WATCH, None),
    "TASTING/FOOD": (
        WATCH,
        "Is this event a tasting menu, food pop-up, chef's table, food trail or special meal?",
    ),
    "TASTING/DRINKS": (
        WATCH,
        "Is this event a wine, beer, whisky or other spirits tasting?",
    ),
    "TASTING/COFFEE-TEA": (
        WATCH,
        "Is this event a coffee or tea tasting or cupping?",
    ),
    "COOKING": (DO, None),
    "COOKING/CLASS": (DO, "At this event, do attendees cook or bake in a class?"),
    "COOKING/MIXOLOGY": (
        DO,
        "At this event, do attendees mix cocktails or other drinks themselves?",
    ),
    "COOKING/COFFEE": (
        DO,
        "At this event, do attendees brew coffee or tea, or make latte art, themselves?",
    ),
    "BOOKS": (None, None),
    "BOOKS/BOOK-CLUB": (DO, "Is this event a book club or group reading session?"),
    "BOOKS/AUTHOR-TALK": (
        WATCH,
        "Is this event a book launch, reading or signing by the book's author, or a conversation with them?",
    ),
    "BOOKS/WRITING": (DO, "Is this event a writing workshop or writing circle?"),
    "SOCIAL": (DO, None),
    "SOCIAL/DATING-MIXER": (DO, "Is this event a singles mixer or dating event?"),
    "SOCIAL/STRANGERS-MEETUP": (
        DO,
        "Is this event a meetup whose stated purpose is for strangers to meet and make new friends?",
    ),
    "PETS": (None, "Is this event about pets or animals, such as a puppy meetup?"),
    "MARKET": (
        WATCH,
        "Is this event a flea market, bazaar, sale or pop-up market?",
    ),
    "KIDS": (
        None,
        "Is this event designed for children, rather than adults who may bring them along?",
    ),
    "COUPLES": (None, "Is this event designed for couples or dates?"),
    # Set only by rules, since who an event is for is not the model's call
    "WOMEN-ONLY": (None, None),
    "TECH": (None, "Is technology, coding or AI the main subject of this event?"),
    "BUSINESS/SKILLS": (
        None,
        "Is this event about running a business, marketing, entrepreneurship, design thinking or personal finance?",
    ),
    "EXPO": (
        None,
        "Is this event a trade expo, education fair, property show or jewellery show selling to visitors?",
    ),
    "ATTRACTION": (
        None,
        "Is this a ticket to a permanent venue such as a play zone, arcade, go-karting track, amusement park or shooting range, rather than a one-off event?",
    ),
    "PROMOTION": (
        None,
        "Is this a promotion for a pub, restaurant or store, such as drink deals or happy hours, rather than an event?",
    ),
    "TRIP": (
        None,
        "Does this event take attendees on a trip or tour to a place outside Bangalore?",
    ),
}
# Hidden events are neither tagged nor merged; the website's excludeTags has these too
EXCLUDE = {"BUSINESS", "LOW-QUALITY", "NOTINBLR", "DANDIYA", "WOOWOO"}


def parent(tag):
    return tag.rpartition("/")[0] or None


def with_parents(tags):
    out = set()
    for tag in tags:
        while tag:
            out.add(tag)
            tag = parent(tag)
    return out


# Tags the model is asked about
QUESTIONS = {tag: q for tag, (_, q) in TAGS.items() if q}


# Tuned on eight weeks of events against hand labels; every other tag uses 0.5
THRESHOLDS = {
    "ART-CRAFT": 0.7,
    "ART-CRAFT/POTTERY": 0.7,
    "ART-CRAFT/CANDLES": 0.85,
    "ART-CRAFT/JEWELLERY": 0.3,
    "ART-CRAFT/PERFUMERY": 0.3,
    "ART-CRAFT/PLANTS": 0.75,
    "SHOW/THEATER": 0.7,
    "SHOW/STORYTELLING": 0.85,
    "LIVE-MUSIC/ROCK-METAL": 0.9,
    "LIVE-MUSIC/SUFI-QAWWALI": 0.75,
    "LIVE-MUSIC/FOLK": 0.8,
    "NIGHTLIFE/DJ": 0.75,
    "NIGHTLIFE/BOLLYWOOD": 0.75,
    "MOVIE-SCREENING": 0.8,
    "GAMES/PUZZLES": 0.7,
    "FITNESS": 0.85,
    "FITNESS/TEAM-SPORTS": 0.8,
    "OUTDOORS/ADVENTURE": 0.75,
    "OUTDOORS/NATURE-WALK": 0.75,
    "TASTING/FOOD": 0.3,
    "COOKING/CLASS": 0.3,
    "TASTING/COFFEE-TEA": 0.7,
    "TASTING/DRINKS": 0.35,
    "BOOKS/AUTHOR-TALK": 0.9,
    "PETS": 0.7,
    "SOCIAL/STRANGERS-MEETUP": 0.9,
    "SHOW/PERFORMANCE-ART": 0.8,
    "BUSINESS/SKILLS": 0.7,
    "COUPLES": 0.7,
    # Demoting tags hide events, so they need more certainty
    "EXPO": 0.6,
    "ATTRACTION": 0.6,
    "PROMOTION": 0.55,
    "TRIP": 0.9,
}

# Asked of every event, but only fills a missing or plain Event type
TYPES = {
    "BusinessEvent": "A business, startup, trade or professional networking event",
    "ChildrensEvent": "An event designed for children",
    "ComedyEvent": "A comedy show, such as stand-up or an improv show",
    "DanceEvent": "A dance performance, dance class or social dance night",
    "EducationEvent": "A workshop, class, course or lecture where attendees learn a skill or subject, including craft workshops",
    "ExhibitionEvent": "An exhibition or display for visitors to view",
    "Festival": "A multi-act festival, fair or cultural celebration",
    "FoodEvent": "A food or drink event, such as a tasting, special meal, cooking class or food festival",
    "LiteraryEvent": "A book launch, reading, book club, poetry or literary event",
    "MusicEvent": "A concert, gig, DJ night or other music performance",
    "ScreeningEvent": "A film or sports screening",
    "SocialEvent": "A meetup, party, game night or other social gathering",
    "SportsEvent": "A sport, fitness or outdoor activity, such as a run, ride, trek or match",
    "TheaterEvent": "A theatre play, drama or puppetry performance",
    "VisualArtsEvent": "A painting, drawing or sketching session",
}
TYPE_CONFIDENCE = 0.5
