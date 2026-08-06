# Helper script to run pytest inside the docker container
Write-Host "Running pytest inside codepy-framework-test container..." -ForegroundColor Cyan
docker compose exec codepy-app pytest
