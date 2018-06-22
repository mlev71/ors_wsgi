import os
from neo4j.v1 import GraphDatabase
from app.components.cel import * 


# will become celery tasks
# change to execution functions

def postDoi(doiData):
    ''' Contains all the logic for posting a doi
    '''

    doi_guid = doiData.get('@id')
    doi_type = doiData.get('@type')
    author = doiData.get('author')
    funder = doiData.get('funder')

    if doi_type == "Dataset":
        content = doiData.get('contentUrl')        
        file_format = doiData.get('fileFormat') 
        assert content is not None
        assert file_format is not None

    # post the Doi as a node
    doi_task = postNeoDoi.delay(doiData)

    # add authors
    if isinstance(author,dict):
        author_task = postNeoAuthor.delay(author, doi_guid)

    if isinstance(author,list):
        author_task = [postNeoAuthor.delay(auth, doi_gid) for auth in author]


    # add funders
    if isinstance(funder,dict):
        funder_task = postNeoFunder.delay(funder, doi_guid)

    if isinstance(funder, list):
        funder_task =[postNeoFunder.delay(funder_elem,doi_guid) for funder_elem in funder] 
   
    # if its a dataset add all downloads and checksums
    if doi_type == "Dataset":
        checksum_list = list(filter(lambda x: isinstance(x,dict), doiData.get('identifier'))) 
        download_task = postNeoDownloads.delay(content, checksum_list,file_format, doi_guid)


def postArk(arkData):
    ''' Adds task to task queue
    '''

    ark_guid = arkData.get('@id')
    ark_type = arkData.get('@type')
    author = arkData.get('author')
    funder = arkData.get('funder')

    if ark_type == "Dataset":
        content = arkData.get('contentUrl', 'None')        
        file_format = arkData.get('fileFormat', 'None') 

    # post the Doi as a node
    ark_task = postNeoArk.delay(arkData)


    # add authors
    if isinstance(author,dict):
        author_task = postNeoAuthor.delay(author, ark_guid)

    if isinstance(author,list):
        author_task = [postNeoAuthor.delay(auth, ark_gid) for auth in author]


    # add funders
    if isinstance(funder,dict):
        funder_task = postNeoFunder.delay(funder, ark_guid)

    if isinstance(funder, list):
        funder_task =[postNeoFunder.delay(funder_elem,ark_guid) for funder_elem in funder] 
   
    # if its a dataset add all downloads and checksums
    if ark_type == "Dataset":
        checksum_list = list(filter(lambda x: isinstance(x,dict), arkData.get('identifier'))) 
        download_task = postNeoDownloads.delay(content, checksum_list,file_format, ark_guid)




class NeoConn():
    ''' Class used to initialize a neo connection
    '''
    uri = "".join(["bolt://",os.environ.get('NEO_URL', "none"), ":7687"])
    user = os.environ.get('NEO_USER')
    password = os.environ.get('NEO_PASSWORD')
                  
    def __init__(self):
        ''' Establish Driver Connection with Neo4j database
        '''
        self.driver = GraphDatabase.driver(uri = self.uri, auth = (self.user, self.password) )


    def getDownloads(self, guid, loc='aws'):    
        with self.driver.session() as session:
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
        if content_data == []:
            return None
        else:
            return [download_node.get('d.url') for download_node in content_data]


    def getCache(self, guid):
        """ Retrieve Any Object by Guid from the Cache
        """
        with self.driver.session() as session:
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


    def deleteCache(self, guid):
        """ Delete an Object and remove all relationships from Cache
        """
        with self.driver.session() as session:
            with session.begin_transaction() as tx:
                # grab properties
                node = tx.run("MATCH (node) "
                      "WHERE node.guid=$guid "
                      "RETURN properties(node)",
                      guid= guid)
                # delete
                tx.run("MATCH (node) "
                      "WHERE node.guid=$guid "
                      "DETACH DELETE node ",
                      guid= guid)
                node_data = node.data()
                if node_data == []:
                    return None
                else:
                    return node_data[0].get('properties(node)')


    def importCache(self, target):
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
