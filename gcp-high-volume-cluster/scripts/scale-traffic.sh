#!/bin/bash
# Scale traffic for specific app
# Usage: ./scale-traffic.sh 3 500  (sets app-3 to 500 users)

APP_NUM=$1
USERS=$2

if [ -z "$APP_NUM" ] || [ -z "$USERS" ]; then
  echo "Usage: ./scale-traffic.sh <app-number> <users>"
  echo "Example: ./scale-traffic.sh 3 500"
  exit 1
fi

echo "Scaling loadgen-$APP_NUM to $USERS users..."
kubectl set env deployment/loadgen-$APP_NUM -n prod USERS=$USERS

echo "Done! Loadgen-$APP_NUM now configured for $USERS users"
