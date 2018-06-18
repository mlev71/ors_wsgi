build-local:
	docker build src/server/. -t ors_wsgi
	docker build src/worker/. -t ors_worker

run-local:	
	docker-compose build
	docker-compose up

restart-wsgi:
	docker-compose kill wsgi
	docker-compose build wsgi
	docker-compose up -d --no-deps wsgi

