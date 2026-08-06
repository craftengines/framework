#!/bin/bash
# Helper script to run pytest inside the docker container
echo -e "\e[36mRunning pytest inside codepy-framework-test container...\e[0m"
docker compose exec codepy-app pytest
