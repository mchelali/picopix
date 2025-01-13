start:
	docker compose -f docker-compose.yaml -p picopix up -d --build
stop:
	docker compose -f docker-compose.yaml -p picopix down

custart:
	docker compose -f docker-compose.cuda.yaml -p picopix up -d --build
custop:
	docker compose -f docker-compose.cuda.yaml -p picopix down

stdev:
	docker compose -f docker-compose.dev.yaml -p picopix up -d --build
spdev:
	docker compose -f docker-compose.dev.yaml -p picopix down
