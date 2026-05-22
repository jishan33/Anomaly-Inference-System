#!/bin/bash
#“Use bash to execute this script”
 # chmod
 # “change mode” (change file permissions)
 # +x
 # “add execute permission”

 # chmod +x load_test.sh
 # ./load_test.sh

# 1. Total requests per wave/burst
BATCH_SIZE=200

# API endpoint
URL="http://localhost:8000/predict_async"

# 2. Calculate the end time (5 minutes = 300 seconds from now)
DURATION=300
END_TIME=$(( $(date +%s) + DURATION ))

echo "Starting burst load test. Running for 5 minutes (until $(date -d @$END_TIME +%T))..."
echo "Sending a wave of $BATCH_SIZE parallel requests every 5 seconds..."

# 3. Keep looping until 5 minutes pass
while [ $(date +%s) -lt $END_TIME ]
do
  echo "--> Firing a wave of $BATCH_SIZE requests..."

  # 4. Launch 200 requests in parallel using backgrounding (&)
  for i in $(seq 1 $BATCH_SIZE)
  do
    AMOUNT=$((RANDOM % 1000 + 1))
    (( RANDOM % 100 + 1 <= 30 )) && TIER="vip" || TIER="free"

    curl -s -X POST $URL \
      -H "Content-Type: application/json" \
      -d "{\"customer_token\":\"C_hello_kitty\",\"amount\":$AMOUNT,\"tier\":\"$TIER\"}" &
  done

  # 5. Wait 2 seconds before launching the next wave
  sleep 2
done

# wait for all background jobs to finish
wait

echo "All waves completed. Load test finished."