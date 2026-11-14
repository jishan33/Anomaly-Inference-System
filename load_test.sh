#!/bin/bash
#“Use bash to execute this script”
 # chmod
 # “change mode” (change file permissions)
 # +x
 # “add execute permission”

 # chmod +x load_test.sh
 # ./load_test.sh

# 1. Total requests per wave/burst
BATCH_SIZE=500

# API endpoint
URL="http://localhost:80/predict_async"

# 2. Calculate the end time (5 minutes = 300 seconds from now)
DURATION=600
END_TIME=$(( $(date +%s) + DURATION ))

echo "Starting burst load test. Running for $(DURATION) seconds (until $(date -d @$END_TIME +%T))..."
echo "Sending a wave of $BATCH_SIZE parallel requests every 2 seconds..."

# 3. Keep looping until 5 minutes pass
while [ $(date +%s) -lt $END_TIME ]
do
  echo "--> Firing a wave of $BATCH_SIZE requests..."

  # 4. Launch x requests in parallel using backgrounding (&)
  for i in $(seq 1 $BATCH_SIZE)
  do
    AMOUNT=$((RANDOM % 1000 + 1))
    CREATED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    case $((RANDOM % 3)) in
        0) TYPE="PAYMENT" ;;
        1) TYPE="REFUND" ;;
        2) TYPE="TRANSFER" ;;
      esac

    TRANSACTION_TOKEN="TXN_$(uuidgen | tr -d '-')"
    CUSTOMER_TOKEN="C_$(uuidgen | tr -d '-' | cut -c 1-28)"

    curl -s -X POST "$URL" \
        -H "Content-Type: application/json" \
        -d "{
          \"customer_token\": \"$CUSTOMER_TOKEN\",
          \"transaction_token\": \"$TRANSACTION_TOKEN\",
          \"amount\": $AMOUNT,
          \"created_at\": \"$CREATED_AT\",
          \"type\": \"$TYPE\"
        }" &
    done

  # 5. Wait 2 seconds before launching the next wave
  sleep 2
done

# wait for all background jobs to finish
wait

echo "All waves completed. Load test finished."