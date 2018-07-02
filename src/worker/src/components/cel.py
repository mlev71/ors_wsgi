############################################################
#                   TASK QUEUE                             #
############################################################
from celery import Celery
import re, requests, os, json
from neo4j.v1 import GraphDatabase
import neo4j.v1

NEO_URI = "".join(["bolt://",os.environ.get('NEO_URL', 'localhost'), ":7687"])
NEO_USER = os.environ.get('NEO_USER', 'neo4j')
NEO_PASSWORD = os.environ.get('NEO_PASSWORD', 'localtest')

REDIS_URL = os.environ.get('REDIS_URL', 'localhost')

celery = Celery(
        'cel',
        backend= 'redis://'+REDIS_URL+':6379',
        broker = 'redis://'+REDIS_URL+':6379' 
        )

# tasks for network requests
@celery.task(name='put_identifier')
def put_task(target, payload, user, password):
    ''' Put a new identifier 

    '''

    # turn into bytes for submission
    payload = outputAnvl(payload)

    auth = requests.auth.HTTPBasicAuth(user, password)
    connect_timeout, read_timeout = 5.0, 30.0
    response = requests.put(
            auth = auth,
            url=target,
            headers = {'Content-Type': 'text/plain; charset=UTF-8'},
            data = payload,
            timeout  = (connect_timeout, read_timeout)
            )


    response_dict = {
            'status_code': response.status_code,
            'content' : response.content.decode('utf-8')
            }

    return response_dict

@celery.task(name='delete_identifier')
def delete_task(target, user, password):
    ''' Delete an identifier
    '''

    auth = requests.auth.HTTPBasicAuth(user, password)
    connect_timeout, read_timeout = 5.0, 30.0
    response = requests.delete(
            auth = auth,
            url=target,
            timeout  = (connect_timeout, read_timeout)
            )

    response_dict = {
        'status_code': response.status_code,
        'content' :response.content.decode('utf-8')
            }

    return response_dict



#################
# DATACITE TASKS# 
#################

@celery.task(name='register_metadata')
def register_metadata(payload, user, password):
    ''' Create a metadata record in Datacite
    ''' 
    auth = requests.auth.HTTPBasicAuth(user, password)
    connect_timeout, read_timeout = 5.0, 30.0

    create_metadata = requests.post(
            url = "https://mds.test.datacite.org/metadata/" ,
            auth = auth,
            data = payload,
            timeout  = (connect_timeout, read_timeout)
            )

    metadata_response = { 
                'status_code': create_metadata.status_code,
                'content': create_metadata.content.decode('utf-8')
                }
    return metadata_response


@celery.task(name='reserve_doi')
def reserve_doi(doi, landing_page, user, password):
    ''' Reserve a Doi for the metadata in datacite
    '''

    auth = requests.auth.HTTPBasicAuth(user, password)
    connect_timeout, read_timeout = 5.0, 30.0

    reserve_doi = requests.put(
            url = "https://mds.test.datacite.org/doi/"+doi,
            auth = auth,
            data = "doi="+doi+"\nurl="+landing_page,
            timeout  = (connect_timeout, read_timeout)
            )

    reservation_response = {
            'status_code': reserve_doi.status_code,
            'content': reserve_doi.content.decode('utf-8')
            }
    return reservation_response


###############
#  NEO TASKS  #
###############

#   Delete by Guid
@celery.task(name="delete_neo_guid")
def deleteNeoByGuid(guid):
    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) )
    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run(
                    "MATCH (n {guid: $guid}) DETACH DELETE n ",
                    guid = guid
                    )


# Put Ark
@celery.task(name="post_neo_ark")
def postNeoArk(data):
    ''' Add a guid node to the neo store
    
    If its a dataset attach it to it's DataCatalog
    '''

    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) )

    guid = data.get('@id')
    name = data.get('name')
    doi_type = data.get('@type')
    includedInDataCatalog = data.get('includedInDataCatalog')
    dateCreated = data.get('dateCreated', 'None') 

    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            if doi_type == "DataCatalog":
                assert name is not None
                assert guid is not None
                assert dateCreated is not None
                ark_record = tx.run(
                        "MERGE (ark:Ark:DataCatalog {name: $name, guid:$guid, dateCreated: $dateCreated}) "
                        "RETURN ark ",
                        name = name,
                        guid = guid,
                        dateCreated = dateCreated
                    )

            if doi_type == "Dataset":
                assert name is not None
                assert guid is not None
                assert dateCreated is not None
                assert includedInDataCatalog is not None
                ark_record = tx.run(
                        "MATCH (dc:DataCatalog {guid: $dcguid})"
                        "MERGE (ark:Ark:Dataset {name: $name, guid: $guid, dateCreated: $dateCreated})-[:includedInDataCatalog]->(dc)"
                        "RETURN ark",
                        dcguid = includedInDataCatalog,
                        name = name,
                        guid = guid,
                        dateCreated = dateCreated
                        )


    node = ark_record.single().data().get('ark')

    properties = dict(node.items())

    response = {
            'id': node.id,
            'labels': list(node.labels),
            'properties': properties
            }

    return response

# Put Doi
@celery.task(name="post_neo_doi")
def postNeoDoi(data):
    ''' Add a guid node to the neo store 
    If its a dataset attach it to it's DataCatalog
    '''

    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) )

    guid = data.get('@id')
    name = data.get('name')
    guid_type = data.get('@type')
    includedInDataCatalog = data.get('includedInDataCatalog')
    datePublished = data.get('datePublished') 

    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            if guid_type == "DataCatalog":
                assert name is not None
                assert guid is not None
                assert datePublished is not None
                doi_record = tx.run(
                        "MERGE (doi:Doi:DataCatalog {name: $name, guid:$guid, datePublished: $datePub}) "
                        "RETURN doi",
                        name = name,
                        guid = guid,
                        datePub = datePublished
                    )

            if guid_type == "Dataset":
                assert name is not None
                assert guid is not None
                assert datePublished is not None
                assert includedInDataCatalog is not None
                doi_record = tx.run(
                        "MATCH (dc:DataCatalog {guid: $dcguid} ) "
                        "MERGE (doi:Doi:Dataset {name: $name, guid: $guid, datePublished: $datePub})-[:includedInDataCatalog]->(dc)"
                        "RETURN doi",
                        dcguid = includedInDataCatalog,
                        name = name,
                        guid = guid,
                        datePub = datePublished
                        )

    node = doi_record.single().data().get('doi')

    response = {
            'id': node.id,
            'labels': list(node.labels),
            'properties': dict(node.items())
            }

    return response


@celery.task(name="post_download")
def postDownload(location, checksumList, fileFormat, datasetGuid, resourceType):
    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) ) 
    with neo_driver.session() as session:
        with session.begin_transaction() as tx:

            if resourceType == "aws":
                dl_record = tx.run(
                    "MATCH (ds:Dataset {guid: $guid})"
                    "MERGE (dl:Download:awsResource {url: $url, fileFormat: $fileFormat})<-[:download]-(ds) "
                    "RETURN dl ",
                    guid = datasetGuid,
                    fileFormat = fileFormat,
                    url = location 
                    )

            if resourceType == "gpc":
                dl_record = tx.run(
                    "MATCH (ds:Dataset {guid: $guid}) "
                    "MERGE (dl:Download:gpcResource {url: $url, fileFormat: $fileFormat})<-[:download]-(ds) "
                    "RETURN dl",
                        guid = datasetGuid,
                        fileFormat = fileFormat,
                        url = location
                        )

            dl_node = dl_record.single().data().get('dl')
            
            dl_data = { 
                    'id': dl_node.id,
                    'labels': list(dl_node.labels),
                    'properties': dict(dl_node.items())
                    }

            cs_nodes = []
            for checksum in checksumList:
                id_type= checksum.get('@type')
                method = checksum.get('name')
                value = checksum.get('value')

                cs_record = tx.run(
                    "MATCH (dl:Download {url: $url, fileFormat: $fileFormat})"
                    "MERGE (cs:Checksum {method: $method, value: $value}) "
                    "MERGE (cs)<-[:checksum]-(dl) "
                    "RETURN cs " ,
                    fileFormat = fileFormat,
                    url = location,
                    guid = datasetGuid,
                    method = method,
                    value = value
                    ) 

                cs_node = cs_record.single().data().get('cs')
                
                cs_data = { 
                        'id': cs_node.id,
                        'labels': list(cs_node.labels),
                        'properties': dict(cs_node.items())
                        }

                cs_nodes.append(cs_data)

    response = {
            'download': dl_data,
            'checksums': cs_nodes
            }

    return response


@celery.task(name="get_download")
def getDownloads(guid, resourceType):
    ''' Return all download data for a specific resourceType
    '''
    # start neo driver
    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) ) 
    with neo_driver.session() as session:
        with session.begin_transaction() as tx:

            # check resource type
            if resourceType == "aws":
                cs_query = tx.run(
                        "MATCH (data {guid: $guid})-[*]->(dl:Download:awsResource)-[:checksum]->(cs) "
                        "RETURN DISTINCT cs",
                        guid = guid
                        )

                dl_query = tx.run(
                        "MATCH (data {guid: $guid})-[*]->(dl:Download:awsResource)-[:checksum]->(cs) "
                        "RETURN DISTINCT dl",
                        guid = guid
                        )

            if resourceType == "gpc":
                cs_query = tx.run(
                        "MATCH (data {guid: $guid})-[*]->(dl:Download:gpcResource)-[:checksum]->(cs) "
                        "RETURN DISTINCT cs",
                        guid = guid
                        )

                dl_query = tx.run(
                        "MATCH (data {guid: $guid})-[*]->(dl:Download:gpcResource)-[:checksum]->(cs) "
                        "RETURN DISTINCT dl",
                        guid = guid
                        )

        cs_records = cs_query.data()
        dl_records = dl_query.data()

        downloads = [record.get('dl').properties for record in dl_records]
        checksums = [record.get('cs').properties for record in cs_records]

        neo_driver.close()

        response = {
                'downloads': downloads,
                'checksums': checksums
                }
        return response



@celery.task(name="post_neo_author")
def postNeoAuthor(author, guid):
    ''' Add Author node to database with relationship to doi
    '''
    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) )

    author_name = author.get('name')
    
    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            if author.get('@type') == "Person":
                # try later to get orchid identifier
                auth_record = tx.run(
                        "MATCH (doi {guid: $guid} )"
                        "MERGE (per:Person:Author {name: $name})-[:AuthorOf]->(doi) "
                        "RETURN per",
                        guid = guid,
                        name= author_name
                        )

            if author.get('@type') == "Organization":
                auth_record = tx.run( 
                        "MATCH (doi {guid: $guid}) " 
                        "MERGE (per:Org:Author {name: $name})-[:AuthorOf]->(doi) "
                        "RETURN per",
                        guid= guid,
                        name= author_name
                        )

    neo_driver.close()
    auth_node = auth_record.single().data().get('per')
    response = {
            'id': auth_node.id,
            'lables': list(auth_node.labels),
            'properties': dict(auth_node.items())
            }
    return response


@celery.task(name="post_neo_funder")
def postNeoFunder(funder, guid):
    ''' Add Funder node to database
    assuming they are all organizations
    '''

    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) )

    funder_name = funder.get('name')
    funder_id = funder.get('@id')

    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            if funder_id is not None and funder_name is not None:        
                funder_record = tx.run( 
                        "MATCH (doi {guid: $guid}) "
                        "MERGE (fund:Funder:Org {name: $name, guid: $fundguid})-[:FunderOf]->(doi)"
                        "RETURN fund",
                        guid = guid,
                        fundguid = funder_id,
                        name = funder_name
                        )
            else:
                funder_record = tx.run( 
                        "MATCH (doi {guid: $guid}) "
                        "MERGE (fund:Funder:Org {name: $name})-[:FunderOf]->(doi) "
                        "RETURN fund",
                        guid = guid,
                        name = funder_name
                        )
    neo_driver.close()

    funder_node = funder_record.single().data().get('fund')

    response = {
            'id': funder_node.id,
            'lables': list(funder_node.labels),
            'properties': dict(funder_node.items())
            }

    return response


# ANVL PROCESSESING

def escape(s):
    return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), s)


def outputAnvl(anvlDict):
    ''' Encode all objects into strings, lists into strings
    '''
    return "\n".join("%s: %s" % (escape(str(name)), escape(str(value) )) for name,value in anvlDict.items()).encode('utf-8')

