start:
	docker compose -f docker-compose.yaml -p picopix up -d --build
stop:
	docker compose -f docker-compose.yaml -p picopix down

stdev:
	# poetry export --without-hashes --format=requirements.txt > requirements.txt &&
	docker compose -f docker-compose.dev.yaml -p picopix up -d --build
spdev:
	docker compose -f docker-compose.dev.yaml -p picopix down
