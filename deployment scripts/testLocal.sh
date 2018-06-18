docker build . -t wsgi_local

# TODO 
# grep docker ps
docker run -p 7687:7687 -e 'NEO4J_AUTH=none' --name=neo_server -d neo4j
docker run -p 8080:8080 -e 'NEO_USER=none' -e 'NEO_PASSWORD=none' -e 'NEO_URL=none' --link neo_server wsgi_local

