import http.client
import json
import urllib
import datetime

conn = http.client.HTTPSConnection("www.goethe.de")
payload = {
  'langId': '1',
  'filterData': json.dumps({
      'adress_IDtxt': 'Bangalore',
      'dateStart': datetime.datetime.now().strftime('%Y-%m-%d 00:00:00'),
      'dateEnd': (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d 23:59:59')
  })
}

headers = {
  'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'
}

conn.request("POST", "/rest/objeventcalendarv3/events/fetchEvents", urllib.parse.urlencode(payload), headers)
for event in json.loads(conn.getresponse().read().decode('utf-8'))['eventItems']:
    print(f"https://www.goethe.de/ins/in/en/ver.cfm?event_id={event['object_id']}")
