############################################################
#                   TASK QUEUE                             #
############################################################
from celery import Celery
import re
import requests
import os
from neo4j.v1 import GraphDatabase
import neo4j.v1



##################################
#               AES CRYPTO       #
##################################

from Crypto.Cipher import AES
from Crypto import Random
import base64
import hashlib

block_size = 32
key = hashlib.sha256("hellothisismycipherkey".encode()).digest()
iv = Random.new().read(AES.block_size)

GLOBAL_CIPHER = AES.new(key, AES.MODE_CBC, iv)

def encrypt(raw, cipher):
        raw = pad(raw)
        return base64.b64encode(iv + cipher.encrypt(raw))

def decrypt(enc, cipher):
    enc = base64.b64decode(enc)
    iv = enc[:AES.block_size]
    return unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')


def pad(s):
    return s + (32 - len(s) % 32) * chr(32 - len(s) % 32)

def unpad(s):
    return s[:-ord(s[len(s)-1:])]


NEO_URI = "".join(["bolt://",os.environ.get('NEO_URL', "none"), ":7687"])
NEO_USER = os.environ.get('NEO_USER')
NEO_PASSWORD = os.environ.get('NEO_PASSWORD')
REDIS_URL = os.environ.get('REDIS_URL')


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



##############

##################
# NEO CACHE TASKS#
##################

#   Delete by Guid
# ================

@celery.task(name="delete_neo_guid")
def deleteNeoByGuid(guid):
    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) )
    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            tx.run(
                    "MATCH (n {guid: $guid}) DETACH DELETE n",
                    guid = guid
                    )


#   Put Ark Tasks                
#============================

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
    datePublished = data.get('datePublished', 'None') 

    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            if doi_type == "DataCatalog":
                assert name is not None
                assert guid is not None
                assert datePublished is not None
                doi_record = tx.run(
                        "MERGE (doi:Ark:DataCatalog {name: $name, guid:$guid, datePublished: $datePub}) ",
                        name = name,
                        guid = guid,
                        datePub = datePublished
                    )

            if doi_type == "Dataset":
                assert name is not None
                assert guid is not None
                assert datePublished is not None
                assert includedInDataCatalog is not None
                doi_record = tx.run(
                        "MATCH (dc:DataCatalog) WHERE dc.guid = $dcguid "
                        "MERGE (doi:Ark:Dataset {name: $name, guid: $guid, datePublished: $datePub}) "
                        "MERGE (doi)-[:includedInDataCatalog]->(dc) ",
                        dcguid = includedInDataCatalog,
                        name = name,
                        guid = guid,
                        datePub = datePublished
                        )


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
                        "MERGE (doi:Doi:DataCatalog {name: $name, guid:$guid, datePublished: $datePub}) ",
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
                        "MATCH (dc:DataCatalog) WHERE dc.guid = $dcguid "
                        "MERGE (doi:Doi:Dataset {name: $name, guid: $guid, datePublished: $datePub})-[:includedInDataCatalog]->(dc) ",
                        dcguid = includedInDataCatalog,
                        name = name,
                        guid = guid,
                        datePub = datePublished
                        )


# Add to downloads
@celery.task(name="post_neo_downloads")
def postNeoDownloads(content, checksum_list,fileFormat, guid):
    ''' Post all the download information and the 
    '''

    neo_driver = GraphDatabase.driver(uri = NEO_URI, auth = (NEO_USER, NEO_PASSWORD) ) 

    aws_location_list = list(filter(lambda x: re.match('aws',x) ,content))
    if len(aws_location_list)>1:
        aws_location = aws_location_list[0]
    else:
        aws_location = None

    gpc_location_list = list(filter(lambda x: re.match('gpc',x) ,content))
    if len(gpc_location_list)>1:
        gpc_location = gpc_location_list[0]
    else:
        gpc_location = None

    downloads = {}

    with neo_driver.session() as session:
        with session.begin_transaction() as tx:
            if aws_location is not None:
                aws_encrypted = encrypt(aws_location, GLOBAL_CIPHER).decode()

                # post aws download attatch to 
                if fileFormat is not None:
                    aws_record = tx.run(
                            "MATCH (doi:Dataset) WHERE doi.guid=$guid "
                            "MERGE (aws:awsDownload {url: $url, fileFormat: $fileFormat}) "
                            "MERGE (doi)-[:download]->(aws) "
                            "RETURN aws",
                            guid = guid,
                            url = aws_encrypted,
                            fileFormat = fileFormat)



                aws_node = aws_record.single().data().get('aws')
                aws_prop = dict(aws_node.items())
                downloads.update({'aws':aws_prop })


            if gpc_location is not None:
                gpc_encrypted = encrypt(gpc_location, GLOBAL_CIPHER).decode()

                # post gpc download attatch to the 
                gpc_record = tx.run(
                    "MATCH (doi:Dataset) WHERE doi.guid=$guid "
                    "MERGE (gpc:gpcDownload {url: $url, fileFormat: $fileFormat}) "
                    "MERGE (doi)-[:download]->(gpc) "
                    "RETURN gpc",
                    guid = guid,
                    url = gpc_encrypted,
                    fileFormat = fileFormat
                    )

            # for every checksum attatch to file
            for checksum in checksum_list:
                id_type= checksum.get('@type')
                method = checksum.get('name')
                value = checksum.get('value')

                # attatch to aws downloads
                tx.run(
                    "MATCH (doi:Dataset)-[:download]->(aws:awsDownload) "
                    "WHERE doi.guid = $guid "
                    "MERGE (cs:Checksum {method: $method, value: $value}) "
                    "MERGE (aws)-[:checksum]->(cs) ",
                    guid = guid,
                    method = method,
                    value = value
                    )
               
                # attatch to gpc downloads
                tx.run(
                    "MATCH (doi:Doi:Dataset)-[:download]->(gpc:gpcDownload) "
                    "WHERE doi.guid = $guid "
                    "MERGE (cs:Checksum {method: $method, value: $value}) "
                    "MERGE (gpc)-[:checksum]->(cs) ",
                    guid = guid,
                    method = method,
                    value = value
                    )
     
    
    neo_driver.close()    

    
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
                        "MATCH (doi) WHERE doi.guid = $guid "
                        "MERGE (per:Person:Author {name: $name}) "
                        "MERGE (per)-[:AuthorOf]->(doi) "
                        "RETURN per",
                        guid = guid,
                        name= author_name
                        )

            if author.get('@type') == "Organization":
                auth_record = tx.run( "MATCH (doi) WHERE doi.guid = $guid " 
                        "MERGE (per:Org:Author {name: $name}) "
                        "MERGE (per)-[:AuthorOf]->(doi)"
                        "RETURN per",
                        guid= guid,
                        name= author_name
                        )

    neo_driver.close()


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
                        "MATCH (doi) WHERE doi.guid = $guid "
                        "MERGE (fund:Funder:Org {name: $name, guid: $fundguid}) "
                        "MERGE (fund)-[:FunderOf]->(doi) "
                        "RETURN fund",
                        guid = guid,
                        fundguid = funder_id,
                        name = funder_name
                        )
            else:
                funder_record = tx.run( 
                        "MATCH (doi) WHERE doi.guid = $guid "
                        "MERGE (fund:Funder:Org {name: $name}) "
                        "MERGE (fund)-[:FunderOf]->(doi) "
                        "RETURN fund",
                        guid = guid,
                        name = funder_name
                        )

    funder_node = funder_record.single().data().get('fund')


    neo_driver.close()

    return dict(funder_node.items())

#================================



def escape(s):
    return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), s)


def outputAnvl(anvlDict):
    ''' Encode all objects into strings, lists into strings
    '''
    return "\n".join("%s: %s" % (escape(str(name)), escape(str(value) )) for name,value in anvlDict.items()).encode('utf-8')


if __name__=="__main__":
    print(delete_task.name)
    print(put_task.name)

