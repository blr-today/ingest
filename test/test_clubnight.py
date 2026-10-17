from src.processors.base import DROP
from src.processors.clubnight import ClubNight

FREE = {"@type": "AggregateOffer", "offers": [{"price": 0}, {"price": 0}]}


def test_free_club_night_is_dropped():
    event = {"@type": "MusicEvent", "name": "Desi Sunday ft. Lijohn", "offers": FREE}
    assert ClubNight.process("u", event) == DROP


def test_ticketed_gig_is_kept():
    offers = {"@type": "AggregateOffer", "offers": [{"price": 1499}]}
    event = {
        "@type": "MusicEvent",
        "name": "Gatecrash presents CKRAFT",
        "offers": offers,
    }
    assert ClubNight.process("u", event) is None


def test_free_non_music_event_is_kept():
    assert ClubNight.process("u", {"@type": "ComedyEvent", "offers": FREE}) is None


def test_paid_stag_entry_is_dropped():
    offers = {
        "offers": [
            {"name": "Couple full cover", "price": 1000},
            {"name": "Stag Full cover", "price": 2000},
        ]
    }
    assert ClubNight.process("u", {"@type": "SocialEvent", "offers": offers}) == DROP


def test_couple_and_ladies_entry_is_dropped():
    offers = {
        "offers": [{"name": "Couples", "price": 100}, {"name": "Ladies", "price": 100}]
    }
    assert ClubNight.process("u", {"@type": "Event", "offers": offers}) == DROP


def test_paid_dj_night_is_dropped():
    offers = {"offers": [{"name": "Cover Charge", "price": 200}]}
    event = {
        "@type": "MusicEvent",
        "name": "Bollywood Night ft. DJ Praxx",
        "offers": offers,
    }
    assert ClubNight.process("u", event) == DROP


def test_couple_comedy_and_live_music_are_kept():
    couple = {
        "offers": [
            {"name": "Regular Ticket", "price": 299},
            {"name": "Couple Ticket", "price": 499},
        ]
    }
    assert ClubNight.process("u", {"@type": "ComedyEvent", "offers": couple}) is None
    live = {
        "@type": "MusicEvent",
        "name": "Live Music ft. Srinisha and DJ Black",
        "offers": couple,
    }
    assert ClubNight.process("u", live) is None
