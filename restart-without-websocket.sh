#!/bin/bash
# Script to restart Open-WebUI with WebSocket completely disabled

echo "Stopping current Open-WebUI container..."
docker stop open-webui
docker rm open-webui

echo "Starting Open-WebUI with WebSocket support completely disabled..."
docker run -d \
  -p 8080:8080 \
  -e ENABLE_WEBSOCKET_SUPPORT=False \
  -e ENABLE_DIRECT_CONNECTIONS=True \
  -e DEFAULT_MODELS=autogpt-slow,autogpt-fast \
  -e ENABLE_REALTIME_CHAT_SAVE="False" \
  -e CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE="0" \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  --add-host=host.docker.internal:host-gateway \
  235046692807.dkr.ecr.us-east-1.amazonaws.com/openmosaics/open-webui

echo "Container started with WebSocket disabled. The frontend should now use polling only."
sleep 5
docker logs open-webui | tail -10
