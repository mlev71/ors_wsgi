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

restart-worker:
	rm src/worker/cel.py
	cp src/server/src/components/cel.py src/worker/cel.py
	docker-compose kill worker
	docker-compose build worker
	docker-compose up -d --no-deps worker

build-all:
	rm src/worker/cel.py
	cp src/server/src/components/cel.py src/worker/cel.py
	docker build src/worker/. -t jackofsum/ors-worker
	docker build src/server/. -t jackofsum/ors-wsgi
	docker push jackofsum/ors-worker
	docker push jackofsum/ors-wsgi
