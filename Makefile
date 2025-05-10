AE_START_TS := $(shell date +%s)
AE_END_TS := $(shell date +%s --date="1 month")

START_TS := $(shell date +"%Y-%m-%d")
END_TS := $(shell date +"%Y-%m-%d" --date="1 month")

TOTAL_ENVIRONMENT_API_TOKEN := $(shell curl_chrome116 --silent --insecure 'https://api.total-environment.com/api/v1.0/token.json' | jq -r '.data.token')

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
	echo "[ALLEVENTS] $$(wc -l $@ | cut -d ' ' -f 1)"

out/te.jsonnet:
	curl_chrome116 --silent --insecure 'https://api.total-environment.com/api/v1.0/getEvents.json' -X POST -H 'content-type: application/json' -H 'Authorization: Bearer $(TOTAL_ENVIRONMENT_API_TOKEN)' --data-raw '{"flag":"upcoming"}' --output $@

out/te.json: out/te.jsonnet
	python src/jsonnet.py out/te.jsonnet || $(call restore-file,$@)

out/skillboxes.jsonnet:
	python src/skillboxes.py 9 || $(call restore-file,$@)

out/skillboxes.json: out/skillboxes.jsonnet
	python src/jsonnet.py out/skillboxes.jsonnet || $(call restore-file,$@)

out/atta_galatta.json:
	python src/atta_galatta.py || $(call restore-file,$@)

out/champaca.json:
	python src/champaca.py || $(call restore-file,$@)

out/highape.txt:
	python src/highape.py | sort > $@ || $(call restore-file,$@)
	echo "[HIGHAPE] $$(wc -l $@ | cut -d ' ' -f 1)"

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
	echo "[INSIDER] $$(wc -l $@ | cut -d ' ' -f 1)"

out/artzo.txt:
	python src/artzo.py | sort > $@ || $(call restore-file,$@)
	echo "[ARTZO] $$(wc -l $@ | cut -d ' ' -f 1)"

out/bhaagoindia.txt:
	python src/bhaagoindia.com.py | sort > $@ ||  $(call restore-file,$@)
	echo "[BHAAGOINDIA] $$(wc -l $@ | cut -d ' ' -f 1)"

# TODO: /exhibits.json is also helpful
# And there are kn translations available as well.
out/scigalleryblr.json:
	python src/scigallery.py || $(call restore-file,$@)

out/venn.json:
	python src/venn.py || $(call restore-file,$@)

out/mmb.txt:
	python src/mmb.py | sort > $@ || $(call restore-file,$@)
	echo "[MMB] $$(wc -l $@ | cut -d ' ' -f 1)"

out/urbanaut.json:
	python src/urbanaut.py  || $(call restore-file,$@)

out/bic.ics:
	curl_chrome116 --silent "https://bangaloreinternationalcentre.org/events/?ical=1" --output $@  || $(call restore-file,$@)

out/bic.json: out/bic.ics
	python src/ics-to-event.py out/bic.ics $@ || $(call restore-file,$@)

out/sofar.json:
	python src/sofar.py || $(call restore-file,$@)

out/sumukha.json:
	python src/sumukha.py || $(call restore-file,$@)

out/timeandspace.json:
	python src/timeandspace.py || $(call restore-file,$@)

out/townscript.txt:
	python src/townscript.py | sort -u > $@ || $(call restore-file,$@)
	echo "[TOWNSCRIPT] $$(wc -l $@ | cut -d ' ' -f 1)"

out/bluetokai.json:
	python src/bluetokai.py || $(call restore-file,$@)

out/gullytours.json:
	python src/gullytours.py || $(call restore-file,$@)

out/tonight.json:
	python src/tonight.py || $(call restore-file,$@)

out/creativemornings.txt:
	python src/creativemornings.py | sort > $@ || $(call restore-file,$@)
	echo "[CREATIVEMORNINGS] $$(wc -l $@ | cut -d ' ' -f 1)"

out/together-buzz.txt:
	python src/together-buzz.py | sort > $@ || $(call restore-file,$@)
	echo "[TOGETHER] $$(wc -l $@ | cut -d ' ' -f 1)"

out/adidas.json:
	python src/adidas.py || $(call restore-file,$@)

out/pvr-cinemas.csv:
	python src/pvr.py || ($(call restore-file,$@); $(call restore-file,"out/pvr-movies.csv"); $(call restore-file,"out/pvr-sessions.csv"))

out/ticketnew-cinemas.csv:
	python src/ticketnew.py || ($(call restore-file,$@); $(call restore-file,"out/ticketnew-movies.csv"); $(call restore-file,"out/ticketnew-sessions.csv"))

out/trove.json:
	python src/trove.py || $(call restore-file,$@)

out/thewhitebox.json:
	python src/thewhitebox.py || $(call restore-file,$@)

out/aceofpubs.ics:
	curl_chrome116 --silent "https://aceofpubs.com/events/category/bengaluru-pub-quiz-event/?post_type=tribe_events&ical=1&eventDisplay=list&ical=1" --output $@ || $(call restore-file,$@)

out/aceofpubs.json: out/aceofpubs.ics
	python src/aceofpubs.py || $(call restore-file,$@)

out/koota.txt:
	curl_chrome116 --silent "https://courtyardkoota.com/event-directory/" | grep -oE 'https://courtyardkoota\.com/events/[a-z0-9-]+/' | sort -u > $@ || $(call restore-file,$@)
		echo "[KOOTA] $$(wc -l $@ | cut -d ' ' -f 1)"

out/sis.json:
	python src/sis.py || $(call restore-file,$@)

out/bcc.json:
	wget -q "https://bangalorechessclub.in/api/upcoming.json" -O $@ || $(call restore-file,$@)

out/pumarun.txt:
	python src/eventbrite.py pumarun | sort > $@ || $(call restore-file,$@)
	echo "[PUMARUN] $$(wc -l $@ | cut -d ' ' -f 1)"

# we just do a minimal transform to remove extra bits we don't need
out/tpcc.jsonnet:
	curl_chrome116 --silent 'https://x2qnegor.apicdn.sanity.io/v2024-09-06/data/query/production?query=*%5B_type+%3D%3D+%22event%22%5D%7B%0A++++++++_id%2C%0A++++++++title%2C%0A++++++++date%2C%0A++++++++online_date%2C%0A++++++++director%2C%0A++++++++note%2C%0A++++++++%22theme%22%3A+theme-%3Etheme%2C%0A++++++++%22poster%22%3A+poster.asset-%3Eurl%2C%0A++++++++%22city%22%3A+city-%3E%7Bcity%2C+color%7D%2C%0A++++++++%22location%22%3A+location-%3E%7Bname%2C+url%7D%2C%0A++++++++rsvpLink%0A++++++%7D&returnQuery=false' | jq \
		'[.result[]|select(.online_date==null) | {id:._id, image:.poster, location:.location, link:.rsvpLink, date:.date, theme:.theme, city:.city.city, title:.title, director: .director} |select(.city=="Bangalore") | select(.date> (now|strftime("%Y-%m-%d")))]' > $@ || $(call restore-file,$@)

out/tpcc.json: out/tpcc.jsonnet
	python src/jsonnet.py out/tpcc.jsonnet || $(call restore-file,$@)

out/lavonne.json:
	python src/lavonne.py || $(call restore-file,$@)

out/bngbirds.json:
	python src/bngbirds.py || $(call restore-file,$@)

out/paintbar.json:
	python src/paintbar.py || $(call restore-file,$@)

out/pedalintandem.json:
	python src/pedalintandem.py || $(call restore-file,$@)

fetch: out/allevents.txt \
 out/highape.txt \
 out/bengalurusustainabilityforum.json \
 out/mapindia.json \
 out/bic.ics \
 out/insider.txt \
 out/bhaagoindia.txt \
 out/scigalleryblr.json \
 out/mmb.txt \
 out/venn.json \
 out/urbanaut.json \
 out/champaca.json \
 out/bic.json \
 out/sumukha.json \
 out/sofar.json \
 out/bluetokai.json \
 out/gullytours.json \
 out/townscript.txt \
 out/together-buzz.txt \
 out/tonight.json \
 out/creativemornings.txt \
 out/adidas.json \
 out/pvr-cinemas.csv \
 out/ticketnew-cinemas.csv \
 out/trove.json \
 out/aceofpubs.json \
 out/atta_galatta.json \
 out/koota.txt \
 out/te.json \
 out/underline.json \
 out/sis.json \
 out/bcc.json \
 out/pumarun.txt \
 out/tpcc.json \
 out/skillboxes.json \
 out/thewhitebox.json \
 out/timeandspace.json \
 out/lavonne.json \
 out/bngbirds.json \
 out/paintbar.json \
 out/artzo.txt
	@echo "Done"

clean:
	rm -rf out/*

build: fetch
	python src/event-fetcher.py

build-sqlite:
	.github/sqlite.sh

post-build: build-sqlite
	LD_PRELOAD=/tmp/sqlite-amalgamation-3490100/libsqlite.so python3 -c "import sqlite3;print(sqlite3.sqlite_version)"
	LD_PRELOAD=/tmp/sqlite-amalgamation-3490100/libsqlite.so python3 -m sqlite3 events.db < post-build.sql

all: build post-build
	@echo "Finished build"
