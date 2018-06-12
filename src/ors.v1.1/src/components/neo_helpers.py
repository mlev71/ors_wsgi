import os
from neo4j.v1 import GraphDatabase

class NeoConn():
    ''' Class used to initialize a neo connection
    '''
    uri = "".join(["bolt://",os.environ.get('NEO_URL', "none"), ":7687"])
    user = os.environ.get('NEO_USER')
    password = os.environ.get('NEO_PASSWORD')
                  
    def __init__(self, local=True):
        if local==True:
            self.driver = GraphDatabase.driver(uri ="bolt://localhost:7687")
        else:
            self.driver = GraphDatabase.driver(uri = self.uri, auth = (self.user, self.password) )


def getDownloads(guid, loc='aws'):
    neo_driver = NeoConn()
    with neo_driver.driver.session() as session:
        with session.begin_transaction() as tx:
            if loc=='aws':
                content = tx.run("MATCH (node)-[*]->(d:AWSdownload) WHERE node.guid=$guid "
                   "RETURN d.url",
                  guid=guid)
            else:
                content = tx.run("MATCH (node)-[*]->(d:GPCdownload) WHERE node.guid=$guid "
                   "RETURN d.url",
                  guid=guid)


    content_data = content.data()
    return [download_node.get('d.url') for download_node in content_data]


def getCache(guid):
    """ Retrieve an Object by its Guid from the Cache
    """

    neo_driver = NeoConn()
    with neo_driver.driver.session() as session:
        with session.begin_transaction() as tx:
            node = tx.run("MATCH (node) "
                   "WHERE node.guid=$guid "
                   "RETURN properties(node)",
                   guid = guid)
            node_data = node.data()
            if node_data == []:
                return None
            else:
                return node_data[0].get('properties(node)', None)


def deleteCache(guid):
    """ Delete an Object and remove all relationships from Cache
    """
    neo_driver = NeoConn()
    with neo_driver.driver.session() as session:
        with session.begin_transaction() as tx:
            node = tx.run("MATCH (node) "
                  "WHERE node.guid=$guid "
                  "RETURN properties(node)",
                  guid= guid)
            tx.run("MATCH (node) "
                  "WHERE node.guid=$guid "
                  "DETACH DELETE node ",
                  guid= guid)
            node_data = node.data()
            if node_data == []:
                return None
            else:
                return node_data[0].get('properties(node)')


def importCache(target):
    """ Send a request to GUID service, import response to cache
    
    From the target determine the object type
    """
    response = requests.get(target)
    anvlDict = ingestAnvl(response.content.decode('utf-8'))
    
    if re.match("ark:/", target):
        obj = Ark(anvlDict)
        
    if re.match("doi:", target):
        obj = Doi(anvlDict)
        
    obj.postNeo()
