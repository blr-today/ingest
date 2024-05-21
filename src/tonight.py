import http.client
import json
import datetime
import re
import os
from urllib.parse import urlencode


def fetch_parties():
    connection = http.client.HTTPSConnection("firestore.googleapis.com")
    connection.request("GET", "/v1/projects/tonight-is/databases/(default)/documents/parties")
    response = connection.getresponse()
    return json.loads(response.read().decode('utf-8'))

def parse_firebase_struct(obj):
    if type(obj) == list:
        return [parse_firebase_struct(x) for x in obj]
    for c in ['stringValue', 'timestampValue', 'booleanValue', 'integerValue', 'nullValue']:
        if c in obj:
            return obj[c]
    if 'fields' in obj:
        for k in obj['fields']:
            obj[k] = parse_firebase_struct(obj['fields'][k])
        del obj['fields']
    if 'mapValue' in obj:
        return parse_firebase_struct(obj['mapValue'])
    if 'arrayValue' in obj:
        if 'values' in obj['arrayValue']:
            x  = parse_firebase_struct(obj['arrayValue']['values'])
        else:
            x = []
        del obj['arrayValue']
        return x
    return obj

with open('fixtures/tonight-is-parties.json', 'r') as f:
    data = parse_firebase_struct(fetch_parties()['documents'])
    with open("out/tonight.json", "w") as file:
        json.dump(data, file, indent=2)
