#!/bin/sh
# Healthcheck: queries LEAVE_REQUESTS (last table seeded) to confirm DB is ready.
#
# Two output destinations:
#   /tmp/hc.log                    — full history, inspect with:
#                                    docker exec relipeople-oracle cat /tmp/hc.log
#   stdout                         — last N entries visible via:
#                                    docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' relipeople-oracle
LOG=/tmp/hc.log

RESULT=$(sqlplus -s -L "$APP_USER/$APP_USER_PASSWORD@//localhost:1521/${ORACLE_DATABASE:-FREEPDB1}" 2>&1 <<'SQLEOF'
SET HEADING OFF
SET FEEDBACK OFF
SELECT 1 FROM LEAVE_REQUESTS WHERE ROWNUM=1;
SQLEOF
)
RC=$?

TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S')
RESULT_ONELINE=$(printf '%s' "$RESULT" | tr -s '[:space:]' ' ' | sed 's/^ //;s/ $//')

if printf '%s' "$RESULT" | grep -qE '^[[:space:]]*1'; then
    STATUS="PASS"
    EXIT=0
else
    STATUS="FAIL"
    EXIT=1
fi

LOG_LINE="${TIMESTAMP}  ${STATUS}  sqlplus_rc=${RC}  result=[${RESULT_ONELINE}]"
printf '%s\n' "$LOG_LINE" >> "$LOG"
printf '%s\n' "$LOG_LINE"   # captured by docker inspect .State.Health.Log

exit $EXIT
