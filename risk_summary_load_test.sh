#!/bin/bash

BATCH_SIZE=${BATCH_SIZE:-500}
URL=${URL:-http://localhost:80/risk_summary/async}
DURATION=120
PAUSE_SECONDS=2
END_TIME=$((SECONDS + DURATION))

echo "Running burst load test for $DURATION seconds against $URL"
echo "Launching up to $BATCH_SIZE requests per wave with a ${PAUSE_SECONDS}s pause."

while (( SECONDS < END_TIME )); do
  echo "--> Launching a wave..."
  CREATED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  for ((i = 0; i < BATCH_SIZE && SECONDS < END_TIME; i++)); do
    AMOUNT=$((RANDOM % 100 + 1))
    RISK_SCORE=$((RANDOM % 11))

    case $((RANDOM % 3)) in
      0) TYPE="PAYMENT" ;;
      1) TYPE="REFUND" ;;
      2) TYPE="TRANSFER" ;;
    esac

    if (( RISK_SCORE < 2 )); then
      RISK_LABEL="LOW_RISK"
    elif (( RISK_SCORE <= 5 )); then
      RISK_LABEL="POTENTIAL_SCAM"
    else
      RISK_LABEL="HIGH_SCAM_RISK"
    fi

    TRANSACTION_TOKEN="TXN_$(uuidgen | tr -d '-')"
    CUSTOMER_TOKEN="C_$(uuidgen | tr -d '-' | cut -c 1-28)"

    curl -sS --max-time 10 \
      -X POST "$URL" \
      -H "Content-Type: application/json" \
      --data-binary "{
        \"customer_token\": \"$CUSTOMER_TOKEN\",
        \"transaction_token\": \"$TRANSACTION_TOKEN\",
        \"amount\": $AMOUNT,
        \"created_at\": \"$CREATED_AT\",
        \"type\": \"$TYPE\",
        \"destination_risk_score\": $RISK_SCORE,
        \"risk_label\": \"$RISK_LABEL\"
      }" &
  done

  REMAINING=$((END_TIME - SECONDS))
  if (( REMAINING > PAUSE_SECONDS )); then
    sleep "$PAUSE_SECONDS"
  elif (( REMAINING > 0 )); then
    sleep "$REMAINING"
  fi
done

wait
echo "All requests finished."