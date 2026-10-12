# Bump VERSION whenever a tag or question changes, so cached answers are asked again
VERSION = 5

# tag: (parent, question asked of every event)
TAGS = {
    "ART-CRAFT": (
        None,
        "At this event, do attendees make an artwork or craft object themselves?",
    ),
    "PAINTING-SKETCHING": (
        "ART-CRAFT",
        "Is painting, drawing or sketching the main activity at this event, such as sip-and-paint or a canvas painting workshop?",
    ),
    "CALLIGRAPHY": (
        "ART-CRAFT",
        "Is this event about calligraphy, hand lettering or typography?",
    ),
    "PRINTMAKING": (
        "ART-CRAFT",
        "Is this event about printmaking, such as linocut, block printing, woodcut or cyanotype?",
    ),
    "POTTERY": (
        "ART-CRAFT",
        "At this event, do attendees work with clay, such as wheel pottery, hand-building or clay modelling?",
    ),
    "RESIN-ART": ("ART-CRAFT", "At this event, do attendees make resin or epoxy art?"),
    "KINTSUGI": (
        "ART-CRAFT",
        "Is this event about kintsugi, the Japanese art of mending pottery with gold?",
    ),
    "CANDLE-MAKING": ("ART-CRAFT", "At this event, do attendees make candles?"),
    "JEWELLERY-MAKING": (
        "ART-CRAFT",
        "At this event, do attendees make wearable jewellery such as earrings, necklaces or bracelets?",
    ),
    "PERFUMERY": (
        "ART-CRAFT",
        "At this event, do attendees make perfume, soap or skincare products?",
    ),
    "PLANTS": (
        "ART-CRAFT",
        "Is this event about terrariums, gardening, plants or flower arranging?",
    ),
    "EXHIBITION": (
        None,
        "Is this event an art, photography or design exhibition for visitors to view?",
    ),
    "PHOTOGRAPHY": (
        None,
        "Is this event about photography, such as a photo walk or photography class?",
    ),
    "THEATER": (
        None,
        "Is this event a theatre play, drama or puppetry performance, or a theatre or acting workshop?",
    ),
    "IMPROV": (None, "Is this event improvisational theatre or improv comedy?"),
    "STANDUP-COMEDY": (None, "Is this event a stand-up comedy show?"),
    "OPEN-MIC": (
        None,
        "Is this event an open mic where attendees can sign up to perform?",
    ),
    "POETRY": (
        None,
        "Is this event about poetry, such as a reading, slam or poetry circle?",
    ),
    "STORYTELLING": (
        None,
        "Is this event a storytelling session, such as folk tales or personal stories told aloud, rather than stand-up comedy?",
    ),
    "MAGIC-SHOW": (None, "Is this event a magic or mentalism show?"),
    "DANCE-PERFORMANCE": (
        None,
        "Is this event a dance performance for an audience, such as contemporary or classical Indian dance?",
    ),
    "LIVE-MUSIC": (
        None,
        "Is live music by musicians or a band the main attraction of this event?",
    ),
    "INDIAN-CLASSICAL": (
        "LIVE-MUSIC",
        "Is this event a Carnatic or Hindustani classical music performance?",
    ),
    "JAZZ": ("LIVE-MUSIC", "Is this event a jazz performance?"),
    "ROCK-METAL": ("LIVE-MUSIC", "Is this event a gig by a rock, metal or punk band?"),
    "SUFI-QAWWALI": (
        "LIVE-MUSIC",
        "Is this event a sufi, qawwali or ghazal performance?",
    ),
    "FOLK-MUSIC": ("LIVE-MUSIC", "Is this event a performance of folk music?"),
    "DEVOTIONAL-MUSIC": (
        "LIVE-MUSIC",
        "Is this event a performance of kirtan, bhajans, chanting or other devotional music?",
    ),
    "DJ-NIGHT": (None, "Is this event a DJ set, club night or party?"),
    "BOLLYWOOD-NIGHT": (
        "DJ-NIGHT",
        "Is this event a DJ night or party that plays Bollywood or other Indian film music?",
    ),
    "KARAOKE": (None, "Is this event a karaoke night?"),
    "JAM-SESSION": (
        None,
        "Is this event a music jam, sing-along or choir where attendees make music together?",
    ),
    "LISTENING-SESSION": (None, "Is this event an album or vinyl listening session?"),
    "MUSIC-LESSON": (None, "Is this event a class to learn an instrument or singing?"),
    "MOVIE-SCREENING": (None, "Is a film or documentary screened at this event?"),
    "SPORTS-SCREENING": (
        None,
        "Is this event a screening of a live sports broadcast for people to watch together?",
    ),
    "F1-SCREENING": (
        "SPORTS-SCREENING",
        "Is this event a screening of a Formula 1 Grand Prix broadcast?",
    ),
    "FOOTBALL-SCREENING": (
        "SPORTS-SCREENING",
        "Is this event a screening of a football match broadcast?",
    ),
    "CRICKET-SCREENING": (
        "SPORTS-SCREENING",
        "Is this event a screening of a cricket match broadcast?",
    ),
    "IPL-SCREENING": (
        "CRICKET-SCREENING",
        "Is this event a screening of an IPL match broadcast?",
    ),
    "BOARDGAMES": (
        None,
        "At this event, do attendees play board games, card games or tabletop games?",
    ),
    "SOCIAL-DEDUCTION": (
        "BOARDGAMES",
        "At this event, do attendees play social deduction games such as Mafia, Werewolf or Blood on the Clocktower?",
    ),
    "TTRPG": (
        "BOARDGAMES",
        "At this event, do attendees play tabletop role-playing games such as Dungeons & Dragons?",
    ),
    "CHESS": (None, "Is this event about chess?"),
    "QUIZZING": (None, "Is this event a quiz or trivia night?"),
    "PUZZLES": (
        None,
        "At this event, do attendees solve jigsaws, crosswords, Rubik's cubes or other puzzles?",
    ),
    "VIDEO-GAMES": (
        None,
        "Is this event about video games, esports or game development?",
    ),
    "FITNESS": (
        None,
        "Is this event a workout, sport or fitness session for attendees?",
    ),
    "RUNNING": (
        "FITNESS",
        "At this event, do attendees go running, such as a run club, fun run or marathon?",
    ),
    "CYCLING": ("FITNESS", "At this event, do attendees cycle, such as a group ride?"),
    "YOGA": ("FITNESS", "Is this event a yoga session?"),
    "PILATES": ("FITNESS", "Is this event a pilates session?"),
    "MARTIAL-ARTS": (
        "FITNESS",
        "Is this event martial arts, boxing or self-defence training?",
    ),
    "CLIMBING": (
        "FITNESS",
        "At this event, do attendees climb, such as bouldering or wall climbing?",
    ),
    "RACKET-SPORTS": (
        "FITNESS",
        "At this event, do attendees play badminton, pickleball, padel, squash or tennis?",
    ),
    "TEAM-SPORTS": (
        "FITNESS",
        "At this event, do attendees play football, basketball, cricket or another team sport?",
    ),
    "DANCE-CLASS": (
        None,
        "At this event, do attendees learn or practise dancing themselves, such as a dance class or social dance night?",
    ),
    "LATIN-DANCE": (
        "DANCE-CLASS",
        "At this event, do attendees dance salsa, bachata or another Latin dance?",
    ),
    "GARBA": ("DANCE-CLASS", "At this event, do attendees dance garba or dandiya?"),
    "ADVENTURE": (
        None,
        "Is this event an adventure activity such as karting, paintball, kayaking, horse riding or shooting?",
    ),
    "LIVE-SPORTS": (
        None,
        "At this event, do attendees watch a live sports match or fight in the stadium or arena?",
    ),
    "HERITAGE-WALK": (None, "Is this event a heritage, history or city walk or tour?"),
    "NATURE-WALK": (
        None,
        "Is this event a guided walk in nature, such as a tree, butterfly or lake walk?",
    ),
    "BIRDING": ("NATURE-WALK", "Is this event birdwatching?"),
    "TREK": (None, "Is this event a trek or hike?"),
    "STARGAZING": (None, "Is this event about stargazing or astronomy?"),
    "FOOD-TASTING": (
        None,
        "Is this event a tasting menu, food pop-up, chef's table, food trail or special meal?",
    ),
    "COOKING-CLASS": (None, "At this event, do attendees cook or bake in a class?"),
    "COFFEE-TEA": (
        None,
        "Is this event about coffee or tea, such as brewing, tasting or latte art?",
    ),
    "DRINKS-TASTING": (
        None,
        "Is this event a wine, beer, whisky or cocktail tasting or mixology session?",
    ),
    "BOOK-CLUB": (None, "Is this event a book club or group reading session?"),
    "AUTHOR-EVENT": (
        None,
        "Is this event a book launch, reading or signing by the book's author, or a conversation with them?",
    ),
    "WRITING": (None, "Is this event a writing workshop or writing circle?"),
    "SCIENCE": (None, "Is science the main subject of this event?"),
    "TECH": (None, "Is technology, coding or AI the main subject of this event?"),
    "HISTORY": (None, "Is history the main subject of this event?"),
    "ENVIRONMENT": (
        None,
        "Is the environment, sustainability, climate or conservation the main subject of this event?",
    ),
    "FILMMAKING": (
        None,
        "At this event, do attendees learn filmmaking, animation or video making?",
    ),
    "DATING-MIXER": (None, "Is this event a singles mixer or dating event?"),
    "STRANGERS-MEETUP": (
        None,
        "Is this event a meetup whose stated purpose is for strangers to meet and make new friends?",
    ),
    "PETS": (None, "Is this event about pets or animals, such as a puppy meetup?"),
    "MARKET": (None, "Is this event a flea market, bazaar, sale or pop-up market?"),
    "KIDS": (
        None,
        "Is this event designed for children, rather than adults who may bring them along?",
    ),
    "WOMEN-ONLY": (None, "Is this event open only to women?"),
    "QUEER": (None, "Is this event a queer or LGBTQ+ event?"),
    "PERFORMANCE-ART": (
        None,
        "Is this event an experimental or multidisciplinary performance mixing movement, video, music or spoken word?",
    ),
    "BUSINESS/SKILLS": (
        None,
        "Is this event about running a business, marketing, entrepreneurship, design thinking or personal finance?",
    ),
    "COUPLES": (None, "Is this event designed for couples or dates?"),
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


def with_parents(tags):
    out = set()
    for tag in tags:
        while tag:
            out.add(tag)
            tag = TAGS[tag][0]
    return out


# Tuned on eight weeks of events against hand labels; every other tag uses 0.5
THRESHOLDS = {
    "ART-CRAFT": 0.7,
    "POTTERY": 0.7,
    "CANDLE-MAKING": 0.85,
    "JEWELLERY-MAKING": 0.3,
    "PERFUMERY": 0.3,
    "PLANTS": 0.75,
    "THEATER": 0.7,
    "STORYTELLING": 0.85,
    "ROCK-METAL": 0.9,
    "SUFI-QAWWALI": 0.75,
    "FOLK-MUSIC": 0.8,
    "DJ-NIGHT": 0.75,
    "BOLLYWOOD-NIGHT": 0.75,
    "MOVIE-SCREENING": 0.8,
    "PUZZLES": 0.7,
    "FITNESS": 0.85,
    "TEAM-SPORTS": 0.8,
    "ADVENTURE": 0.75,
    "NATURE-WALK": 0.75,
    "FOOD-TASTING": 0.3,
    "COOKING-CLASS": 0.3,
    "COFFEE-TEA": 0.7,
    "DRINKS-TASTING": 0.35,
    "AUTHOR-EVENT": 0.9,
    "PETS": 0.7,
    "STRANGERS-MEETUP": 0.9,
    "PERFORMANCE-ART": 0.8,
    "BUSINESS/SKILLS": 0.7,
    "COUPLES": 0.7,
    # Demoting tags hide events, so they need more certainty
    "EXPO": 0.6,
    "ATTRACTION": 0.6,
    "PROMOTION": 0.55,
    "TRIP": 0.9,
}
