# curl-impersonate's newest Chrome profile, keep in sync with .github/workflows/build.yml
CURL_CHROME := curl_chrome150

AE_START_TS := $(shell date +%s)
AE_END_TS := $(shell date +%s --date="1 month")

START_TS := $(shell date +"%Y-%m-%d")

.DEFAULT_GOAL := all

define restore-file
	(echo "FAIL $1" && git checkout -- $1 && echo "RESTORED $1")
endef

out/%.json:
	python -m src.sources $* || $(call restore-file,$@)

out/district.json:
	python -m src.sources district || (echo "FAIL $@" && echo '[]' > $@)

out/bookmyshow.json:
	python -m src.sources bookmyshow || (echo "FAIL $@" && echo '[]' > $@)

out/instagram.json:
	python -m src.sources instagram || (echo "FAIL $@" && echo '[]' > $@)

out/manual.json: in/manual.json
	cp in/manual.json $@

out/allevents.json: out/allevents.txt
out/koota.json: out/koota.txt
out/bic.json: out/bic.ics
out/iiwc.json: out/iiwc.ics
out/afbangalore.json: out/afbangalore.ics
out/cksl.json: out/cksl.ics
out/te.json: out/te.jsonnet
out/underline.json: out/underline.jsonnet
out/tpcc.json: out/tpcc.jsonnet

out/allevents.txt:
	$(CURL_CHROME) --silent --cookie-jar /tmp/allevents.cookies https://allevents.in/ -o /dev/null
	$(CURL_CHROME) --silent --cookie /tmp/allevents.cookies --request POST \
	  --url https://allevents.in/api/index.php/categorization/web/v1/list \
	  --header 'Referer: https://allevents.in/bangalore/all' \
	  --header "Content-Type: application/json" \
	  --data-raw '{"venue": 0,"page": 1,"rows": 100,"tag_type": null,"sdate": $(AE_START_TS),"edate": $(AE_END_TS),"city": "bangalore","keywords": 0,"category": ["all"],"formats": 0,"sort_by_score_only": true}' | \
	  jq -r '.item[] | .share_url' | sort > $@ || $(call restore-file,$@)
	echo "[ALLEVENTS] $$(wc -l < $@) urls"

out/koota.txt:
	$(CURL_CHROME) --silent "https://courtyardkoota.com/event-directory/" | grep -oE 'https://courtyardkoota\.com/events/[a-z0-9-]+/' | sort -u > $@ && test -s $@ || $(call restore-file,$@)
	echo "[KOOTA] $$(wc -l < $@) urls"

out/bic.ics:
	$(CURL_CHROME) --silent "https://bangaloreinternationalcentre.org/events/?ical=1" --output $@  || $(call restore-file,$@)

out/iiwc.ics:
	$(CURL_CHROME) --silent "https://iiwc.in/events/?ical=1" --output $@ || $(call restore-file,$@)

out/afbangalore.ics:
	curl --silent --location "https://bangalore.afindia.org/events.ics" --output $@ || $(call restore-file,$@)

out/cksl.ics:
	wget -q https://calendar.google.com/calendar/ical/c_0tfecbctgj9m3ei54jihee4u0c%40group.calendar.google.com/public/basic.ics -O $@ || $(call restore-file,$@)

out/te.jsonnet:
	token=$$($(CURL_CHROME) --silent --insecure 'https://api.total-environment.com/api/v1.0/token.json' | jq -r '.data.token') && \
	$(CURL_CHROME) --silent --insecure 'https://api.total-environment.com/api/v1.0/getEvents.json' -X POST -H 'content-type: application/json' -H "Authorization: Bearer $$token" --data-raw '{"flag":"upcoming"}' --output $@

out/underline.jsonnet:
	wget -q "https://underline.center/discourse-post-event/events.json?include_details=true&order=desc&after=$(START_TS)" -O $@ || $(call restore-file,$@)

out/tpcc.jsonnet:
	$(CURL_CHROME) --silent 'https://x2qnegor.apicdn.sanity.io/v2024-09-06/data/query/production?query=*%5B_type+%3D%3D+%22event%22%5D%7B%0A++++++++_id%2C%0A++++++++title%2C%0A++++++++date%2C%0A++++++++online_date%2C%0A++++++++director%2C%0A++++++++note%2C%0A++++++++%22theme%22%3A+theme-%3Etheme%2C%0A++++++++%22poster%22%3A+poster.asset-%3Eurl%2C%0A++++++++%22city%22%3A+city-%3E%7Bcity%2C+color%7D%2C%0A++++++++%22location%22%3A+location-%3E%7Bname%2C+url%7D%2C%0A++++++++rsvpLink%0A++++++%7D&returnQuery=false' | jq \
		'[.result[]|select(.online_date==null) | {id:._id, image:.poster, location:.location, link:.rsvpLink, date:.date, theme:.theme, city:.city.city, title:.title, director: .director} |select(.city=="Bangalore") | select(.date> (now|strftime("%Y-%m-%d")))]' > $@ || $(call restore-file,$@)

out/ticketnew/cinemas.csv:
	mkdir -p out/ticketnew
	python -m src.sources.ticketnew || echo "[TICKETNEW] FAILED";

fetch: out/allevents.json \
 out/highape.json \
 out/mapindia.json \
 out/district.json \
 out/bhaagoindia.json \
 out/scigalleryblr.json \
 out/goethe.json \
 out/puttingscene.json \
 out/urbanaut.json \
 out/champaca.json \
 out/bic.json \
 out/sumukha.json \
 out/sofar.json \
 out/bluetokai.json \
 out/gullytours.json \
 out/tonight.json \
 out/creativemornings.json \
 out/adidas.json \
 out/ticketnew/cinemas.csv \
 out/trove.json \
 out/attagalatta.json \
 out/koota.json \
 out/te.json \
 out/underline.json \
 out/sistersinsweat.json \
 out/bcc.json \
 out/pumarun.json \
 out/hsrmeetups.json \
 out/bbb.json \
 out/tpcc.json \
 out/skillboxes.json \
 out/thewhitebox.json \
 out/timeandspace.json \
 out/lavonne.json \
 out/blrbirders.json \
 out/paintbar.json \
 out/artzo.json \
 out/pedalintandem.json \
 out/cksl.json \
 out/sabha.json \
 out/indiarunning.json \
 out/penciljam.json \
 out/mainmission.json \
 out/iiwc.json \
 out/afbangalore.json \
 out/rangashankara.json \
 out/bookmyshow.json \
 out/bac.json \
 out/aceofpubs.json \
 out/fillum.json \
 out/gcw.json \
 out/manual.json \
 out/instagram.json
	@echo "Done"

clean:
	rm -rf out/*

build: fetch
	python -m src.build

# post-build.sql uses ->>, which needs SQLite 3.38; uv's Python bundles a newer one
post-build:
	@echo "Running post-build steps"
	python -m src.processors
	python -c "import sqlite3; print(sqlite3.sqlite_version); assert sqlite3.sqlite_version_info >= (3, 38)"
	python -m sqlite3 events.db < post-build.sql
	python -m src.tagger
	python -m src.dedup
	python -m src.event_ids
	python -m src.validator --output report.json

all: build post-build
	@echo "Finished build"
