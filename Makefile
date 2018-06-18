build-local:
	docker build src/server/. -t ors_wsgi
	docker build src/worker/. -t ors_worker

run-local:	
	docker-compose build
	docker-compose up



