import json

from common.firebase import Firebase

FIXTURE = "test/fixtures/firebase/parties.json"


def test_firestore_document_is_flattened():
    [party] = Firebase.parse_firebase_struct(json.load(open(FIXTURE))["documents"])
    assert party["name"] == "U2 Much - A Tribute to the Legendary Band"
    assert party["featured"] is False
    assert party["startDate"] == "2025-05-10T13:30:00Z"
    assert party["youtubeUrl"] is None
    assert party["featuredImages"] == []
    assert party["genreIds"] == ["housD"]
    assert party["genres"] == [{"id": "housD", "name": "Rock"}]
    assert party["bannerImages"][0]["lastModifiedTS"] == "1746526876401"
    assert party["venues"][0]["location"] == "12.9327477,77.6346542"
    assert "fields" not in party
    assert party["createTime"] == "2025-05-06T10:21:16.484047Z"


def test_scalars_and_plain_objects():
    assert Firebase.parse_firebase_struct({"integerValue": "7"}) == "7"
    assert Firebase.parse_firebase_struct({"mapValue": {}}) == {}
    assert Firebase.parse_firebase_struct({"other": 1}) == {"other": 1}
