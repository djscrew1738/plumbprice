#!/usr/bin/env bash
# Purge Cloudflare edge cache for the ctlplumbingllc.com zone (including app.ctlplumbingllc.com)
#
# Usage:
#   CF_API_TOKEN=your_token ./scripts/purge-cloudflare-cache.sh
#
# Or with Global API Key:
#   CF_EMAIL=you@example.com CF_API_KEY=your_key ./scripts/purge-cloudflare-cache.sh
#
# You can find these in your Cloudflare dashboard:
#   My Profile -> API Tokens -> Create Token (Zone:Cache Purge:Purge)

set -euo pipefail

ZONE_NAME="ctlplumbingllc.com"

# Auth headers
if [ -n "${CF_API_TOKEN:-}" ]; then
  AUTH_HEADER="Authorization: Bearer $CF_API_TOKEN"
elif [ -n "${CF_EMAIL:-}" ] && [ -n "${CF_API_KEY:-}" ]; then
  AUTH_HEADER="X-Auth-Key: $CF_API_KEY"
  EMAIL_HEADER="X-Auth-Email: $CF_EMAIL"
else
  echo "Error: Set CF_API_TOKEN or (CF_EMAIL + CF_API_KEY)"
  echo "  CF_API_TOKEN=xxx $0"
  exit 1
fi

# Get zone ID
echo "Looking up zone ID for $ZONE_NAME..."
ZONE_RESP=$(curl -s "https://api.cloudflare.com/client/v4/zones?name=$ZONE_NAME" \
  -H "$AUTH_HEADER" ${EMAIL_HEADER:+-H "$EMAIL_HEADER"})

ZONE_ID=$(echo "$ZONE_RESP" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('success') and data.get('result'):
    print(data['result'][0]['id'])
else:
    print('ERROR')
")

if [ "$ZONE_ID" = "ERROR" ]; then
  echo "Failed to get zone ID. Check credentials."
  echo "$ZONE_RESP" | python3 -m json.tool 2>/dev/null || echo "$ZONE_RESP"
  exit 1
fi

echo "Zone ID: $ZONE_ID"
echo "Purging all cached content..."

PURGE_RESP=$(curl -s -X POST \
  "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "$AUTH_HEADER" ${EMAIL_HEADER:+-H "$EMAIL_HEADER"} \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}')

SUCCESS=$(echo "$PURGE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success','false'))")

if [ "$SUCCESS" = "True" ]; then
  echo "✅ Cache purged successfully!"
  echo "The site should now serve fresh content within 30 seconds."
else
  echo "❌ Cache purge failed:"
  echo "$PURGE_RESP" | python3 -m json.tool 2>/dev/null || echo "$PURGE_RESP"
  exit 1
fi
