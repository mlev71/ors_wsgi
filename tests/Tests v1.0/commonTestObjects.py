# For All Testing there ought to be consistent objects stored here 

# minid test
minidJSON = {"identifier": "ark:/99999/fk4r8776t",
            "created": "2015-11-10 04:44:44.387671",
            "creator": "0000-0003-2129-5269",
            "checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f",
            "checksumMethod": "sha1",
            "status": "ACTIVE",
            "locations": ["http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf"],
            "titles": ["minid: A BD2K Minimal Viable Identifier Pilot v0.1"]}

################################
# SOLO OBJECTS: not for minting#
################################

# dataCatalog
dcJSON = {"@context" : "http://schema.org", 
        "@id" : "ark:/99999/fk4DataCatalogTestDC", 
        "@type": "DataCatalog", 
        "identifier" : "ark:/99999/fk4DataCatalogTestDC", 
        "url": "https://www.gtexportal.org/home/", 
        "name": "GTEx Portal"}

dcGET = "ark:/99999/fk4DataCatalogTestDC"


################################
# Dataset test objects         #
################################

# dataCatalog 
dsJSON = {"@context": "http://schema.org",
        "@type": "Dataset",
        "@id": "ark:/99999/fk4GTExDS", 
        "identifier": "ark:/99999/fk4DatasetTestDS", 
        "url": "https://www.gtexportal.org/home/", 
        "includedInDataCatalog": "ark:/99999/fk4DatasetTestDC", 
        "dateCreated": "01-29-2018"}


# dataDownload
ddJSON = {"@context": "http://schema.org",
        "@type": "DatasetDownload" , 
        "@id": "ark:/99999/fk4DownloadTestDD",
        "identifier": "ark:/99999/fk4DownloadTestDD", 
        "version": "1.0.0", 
        "includedInDataset": "ark:/99999/fk4DownloadTestDS", 
        "contentSize": "100 bytes", 
        "fileFormat": ".bam",
        "contentUrl": "http://example.org",
        "checksum": "madeupchecksum123",
        "checksumMethod": "md5",
        "filename": "hello.txt"}




#####################
# DSdataCatalog Test#
#####################


DSdcJSON = {"@context" : "http://schema.org", 
        "@id" : "ark:/99999/fk4DatasetTestDC", 
        "@type": "DataCatalog", 
        "identifier": "ark:/99999/fk4DatasetTestDC", 
        "name": "GTEx Portal"}

DSdsJSON = {"@context": "http://schema.org",
        "@type": "Dataset",
        "@id": "ark:/99999/fk4GTExDS", 
        "identifier": "ark:/99999/fk4DatasetTestDS", 
        "includedInDataCatalog": "ark:/99999/fk4DatasetTestDC", 
        "dateCreated": "01-29-2018"}



####################
# DataDownload Test#
####################

DDdcJSON = {"@context" : "http://schema.org", 
        "@id" : "ark:/99999/fk4DownloadTestDC", 
        "@type": "DataCatalog", 
        "identifier": "https://www.gtexportal.org/home/", 
        "name": "GTEx Portal"}  

DDdsJSON = {"@context": "http://schema.org",
        "@type": "Dataset",
        "@id": "ark:/99999/fk4DownloadTestDS", 
        "identifier": "ark:/99999/fk4DownloadTestDS", 
        "includedInDataCatalog": "ark:/99999/fk4DownloadTestDC", 
        "dateCreated": "01-29-2018"}


DDddJSON = {"@context": "http://schema.org",
        "@type": "DatasetDownload" , 
        "@id": "ark:/99999/fk4DownloadTestDD",
        "identifier": "ark:/99999/fk4DownloadTestDD", 
        "version": "1.0.0", 
        "includedInDataset": "ark:/99999/fk4DownloadTestDS", 
        "contentSize": "100 bytes", 
        "fileFormat": ".bam",
        "contentUrl": "http://example.org",
        "checksum": "madeupchecksum123",
        "checksumMethod": "md5",
        "filename": "hello.txt"}


#################
# ANVL TESTS    #
#################
