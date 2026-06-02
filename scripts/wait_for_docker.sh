#!/bin/bash
# Wait for Docker Desktop to be ready (max 60s)
i=0
while ! docker info >/dev/null 2>&1; do
    i=$((i+1))
    if [ $i -ge 20 ]; then
        echo "ERROR: Docker not available after 60s"
        exit 1
    fi
    echo "Waiting for Docker... ($i/20)"
    sleep 3
done
echo "Docker is ready."
