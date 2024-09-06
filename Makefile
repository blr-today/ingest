AE_START_TS := $(shell date +%s)
AE_END_TS := $(shell date +%s --date="1 month")

START_TS := $(shell date +"%Y-%m-%d")
END_TS := $(shell date +"%Y-%m-%d" --date="1 month")

TOTAL_ENVIRONMENT_API_TOKEN := $(shell curl_chrome116 --silent --insecure 'https://api.total-environment.com/api/v1.0/token.json' | jq -r '.data.token')
TPCC_CALENDAR_WIDGET_ID := da2c7ec1-91d2-4b82-a97b-43803ad416a2

define restore-file
	(echo "FAIL $1" && git checkout -- $1 && echo "RESTORED $1")
endef

out/allevents.txt:
	curl_chrome116 --silent --cookie-jar /tmp/allevents.cookies https://allevents.in/ -o /dev/null
	curl_chrome116 --silent --cookie /tmp/allevents.cookies --request POST \
	  --url https://allevents.in/api/index.php/categorization/web/v1/list \
	  --header 'Referer: https://allevents.in/bangalore/all' \
	  --header "Content-Type: application/json" \
	  --data-raw '{"venue": 0,"page": 1,"rows": 100,"tag_type": null,"sdate": $(AE_START_TS),"edate": $(AE_END_TS),"city": "bangalore","keywords": 0,"category": ["all"],"formats": 0,"sort_by_score_only": true}' | \
	  jq -r '.item[] | .share_url' | sort > $@ || $(call restore-file,$@)

# Input file goes here
out/te.jsonnet:
	curl_chrome116 --silent --insecure 'https://api.total-environment.com/api/v1.0/getEvents.json' -X POST -H 'content-type: application/json' -H 'Authorization: Bearer $(TOTAL_ENVIRONMENT_API_TOKEN)' --data-raw '{"flag":"upcoming"}' --output $@

out/te.json: out/te.jsonnet
	python src/jsonnet.py out/te.jsonnet

out/skillboxes.txt:
	python src/skillboxes.py | sort -u > $@ || $(call restore-file,$@)

out/atta_galatta.json:
	python src/atta_galatta.py || $(call restore-file,$@)

out/champaca.json:
	python src/champaca.py || $(call restore-file,$@)

out/highape.txt:
	python src/highape.py | sort > $@ || $(call restore-file,$@)

out/mapindia.ics:
	python src/mapindia.py || $(call restore-file,$@)

out/mapindia.json: out/mapindia.ics
	python src/ics-to-event.py out/mapindia.ics $@ || $(call restore-file,$@)

out/bengalurusustainabilityforum.ics:
	curl_chrome116 --silent "https://www.bengalurusustainabilityforum.org/?post_type=tribe_events&ical=1&eventDisplay=list" --output $@ || $(call restore-file,$@)

out/bengalurusustainabilityforum.json: out/bengalurusustainabilityforum.ics
	python src/ics-to-event.py out/bengalurusustainabilityforum.ics $@ || $(call restore-file,$@)

out/underline.jsonnet:
	wget -q "https://underline.center/discourse-post-event/events.json?include_details=true" -O $@ || $(call restore-file,$@)

out/underline.json: out/underline.jsonnet
	python src/jsonnet.py out/underline.jsonnet || $(call restore-file,$@)

out/insider.txt:
	curl_chrome116 --silent \
	--url 'https://api.insider.in/home?city=bengaluru&eventType=physical&filterBy=go-out&norm=1&select=lite&typeFilter=physical' | \
	jq -r '.list.masterList|keys[]|["https://insider.in",., "event"]|join("/")' | sort > $@ ||  $(call restore-file,$@)

out/bhaagoindia.txt:
	python src/bhaagoindia.com.py | sort > $@ ||  $(call restore-file,$@)

# TODO: /exhibits.json is also helpful
# And there are kn translations available as well.
out/scigalleryblr.json:
	python src/scigallery.py || $(call restore-file,$@)

out/venn.json:
	python src/venn.py || $(call restore-file,$@)

out/mmb.txt:
	python src/mmb.py | sort > $@ || $(call restore-file,$@)

out/urbanaut.json:
	python src/urbanaut.py  || $(call restore-file,$@)

out/zomato.jsonnet:
	python src/zomato.py || $(call restore-file,$@)

out/zomato.json: out/zomato.jsonnet
	python src/jsonnet.py out/zomato.jsonnet || $(call restore-file,$@)

out/bic.ics:
	curl_chrome116 --silent "https://bangaloreinternationalcentre.org/events/?ical=1" --output $@  || $(call restore-file,$@)

out/bic.json: out/bic.ics
	python src/ics-to-event.py out/bic.ics $@ || $(call restore-file,$@)

out/sofar.json:
	python src/sofar.py || $(call restore-file,$@)

out/sumukha.json:
	python src/sumukha.py || $(call restore-file,$@)

out/townscript.txt:
	python src/townscript.py | sort -u > $@ || $(call restore-file,$@)

out/bluetokai.json:
	python src/bluetokai.py || $(call restore-file,$@)

out/gullytours.json:
	python src/gullytours.py || $(call restore-file,$@)

out/tonight.json:
	python src/tonight.py || $(call restore-file,$@)

out/creativemornings.txt:
	python src/creativemornings.py | sort > $@ || $(call restore-file,$@)

out/together-buzz.txt:
	python src/together-buzz.py | sort > $@ || $(call restore-file,$@)

out/adidas.json:
	python src/adidas.py || $(call restore-file,$@)

out/pvr/cinemas.json:
	python src/pvr.py || $(call restore-file,$@)

out/trove.json:
	python src/trove.py || $(call restore-file,$@)

out/aceofpubs.ics:
	curl_chrome116 --silent "https://aceofpubs.com/events/category/bengaluru-pub-quiz-event/?post_type=tribe_events&ical=1&eventDisplay=list&ical=1" --output $@ || $(call restore-file,$@)

out/aceofpubs.json: out/aceofpubs.ics
	python src/aceofpubs.py || $(call restore-file,$@)

out/koota.txt:
	curl_chrome116 --silent "https://courtyardkoota.com/event-directory/" | grep -oE 'https://courtyardkoota\.com/events/[a-z0-9-]+/' | sort -u > $@ || $(call restore-file,$@)

out/sis.json:
	python src/sis.py || $(call restore-file,$@)

out/bcc.json:
	wget -q "https://bangalorechessclub.in/api/upcoming.json" -O $@ || $(call restore-file,$@)

out/pumarun.txt:
	python src/eventbrite.py pumarun | sort > $@ || $(call restore-file,$@)

# we just do a minimal transform to remove extra bits we don't need
out/tpcc.jsonnet:
	curl_chrome116 --silent "https://core.service.elfsight.com/p/boot/?page=https%3A%2F%2Ftpcc.club%2F&w=$(TPCC_CALENDAR_WIDGET_ID)" | jq '.data.widgets["$(TPCC_CALENDAR_WIDGET_ID)"].data.settings | {events: .events | map(select(.start.date > (now|strftime("%Y-%m-%d")))), locations: (.locations | map({id: .id, name: .name, address:.address})), eventTypes: (.eventTypes|map({id:.id, name:.name}))}' > $@ || $(call restore-file,$@)

out/tpcc.json: out/tpcc.jsonnet
	python src/jsonnet.py out/tpcc.jsonnet || $(call restore-file,$@)

fetch: out/allevents.txt \
 out/highape.txt \
 out/mapindia.json \
 out/bic.ics \
 out/insider.txt \
 out/bengalurusustainabilityforum.json \
 out/bhaagoindia.txt \
 out/scigalleryblr.json \
 out/mmb.txt \
 out/venn.json \
 out/zomato.json \
 out/urbanaut.json \
 out/champaca.json \
 out/bic.json \
 out/sumukha.json \
 out/sofar.json \
 out/bluetokai.json \
 out/gullytours.json \
 out/townscript.txt \
 out/together-buzz.txt \
 out/skillboxes.txt \
 out/tonight.json \
 out/creativemornings.txt \
 out/adidas.json \
 out/pvr/cinemas.json \
 out/trove.json \
 out/aceofpubs.json \
 out/atta_galatta.json \
 out/koota.txt \
 out/te.json \
 out/underline.json \
 out/sis.json \
 out/bcc.json \
 out/pumarun.txt \
 out/tpcc.json

	@echo "Done"

clean:
	rm -rf out/*

all: fetch
	python src/event-fetcher.py
	sqlite3 events.db < pre-build.sql
