from src.processors.base import DROP
from src.processors.clubnight import ClubNight

FREE = {"@type": "AggregateOffer", "offers": [{"price": 0}, {"price": 0}]}


def test_free_club_night_is_dropped():
    event = {"@type": "MusicEvent", "name": "Desi Sunday ft. Lijohn", "offers": FREE}
    assert ClubNight.process("u", event) == DROP


def test_ticketed_gig_is_kept():
    offers = {"@type": "AggregateOffer", "offers": [{"price": 1499}]}
    event = {"@type": "MusicEvent", "name": "Gatecrash presents CKRAFT", "offers": offers}
    assert ClubNight.process("u", event) is None


def test_free_non_music_event_is_kept():
    assert ClubNight.process("u", {"@type": "ComedyEvent", "offers": FREE}) is None
