#!/bin/sh
# Auto-run by the official nginx:alpine entrypoint before nginx starts.
# Templates the NREUM snippet's account values into index.html at container
# start, since this app has no backend to do server-side injection.
set -e

TEMPLATE=/usr/share/nginx/templates/index.html.template
OUTPUT=/usr/share/nginx/html/index.html

if [ -f "$TEMPLATE" ]; then
  envsubst '${NEW_RELIC_ACCOUNT_ID} ${NEW_RELIC_TRUST_KEY} ${NEW_RELIC_AGENT_ID} ${NEW_RELIC_LICENSE_KEY} ${NEW_RELIC_APPLICATION_ID}' \
    < "$TEMPLATE" > "$OUTPUT"
fi
