from cel import *
import unittest


EZID_USER = 'apitest'
EZID_PASSWORD = 'apitest'

class ArkTests(unittest.TestCase):


    def test_post_test(self):
        target = "".join([self.endpoint, self.data.get('@id',None) ]) 


        # remove the cloud location keys if they are in the payload
        #if data.get('contentUrl') is not None:
            # encrypt cloud locations
            #data.pop('contentUrl')

        # format payload
        payload = profileFormat(flatten(self.data))
        payload.update(self.options)            


        # add put commmand to task queue
        submission_task= put_task.delay(target=target,payload=payload, user=self.auth[0], password=self.auth[1])

        # if the time to live is set, delete in that amount of time
        if self.options.get('ttl') is not None:
            del_task = delete_task.apply_async(
                    (target, self.auth[0], self.auth[1]),
                    countdown = float(self.options.get('ttl') )
                    )

        return submission_task

    def test_mint_ark(self):        
        ark_task = postNeoArk.delay(self.ark)
        ark_task.get()
        result = ark_task.result

        # expected return 

    def post_authors(self):
        author = self.ark.get('author')

        # add authors
        if isinstance(author,dict):
            author_task = postNeoAuthor.delay(author, ark_guid)
            task_result = author_task.get()


        if isinstance(author,list):
            author_task = [postNeoAuthor.delay(auth, ark_guid) for auth in author]
            task_result = [ task.get() for task in author_task]

            # loop over assertions
            for res in task_result:
                pass
    
    def post_funders(self):
        funder = self.ark.get('funder')



class ArkOneAuth():
    ark =  { 
            "@context": "http://schema.org",
            "@id": "testDConeAuth",
            "identifier": "testDConeAuth",
            "@type": "DataCatalog",
            "url": "http://example.org",
            "name": "Ark DataCatalog",
            "author": {
                "@id": "http://orcid.org/0000-0003-2129-5269",
                "@type": "Person",
                "name": "Ian Foster"
                },
            "datePublished": "2015-11-10T04:44:44.387671Z"
    }


class ArkManyAuth():
    ark=  { 
            "@context": "http://schema.org",
            "@id": "testDConeAuth",
            "identifier": "testDConeAuth",
            "@type": "DataCatalog",
            "url": "http://example.org",
            "name": "Ark DataCatalog",
            "author": [
                {
                "@id": "http://orcid.org/0000-0003-2129-5269",
                "@type": "Person",
                "name": "Ian Foster"
                },

                {
                "@id": "http://orcid.org/randomOrchid",
                "@type": "Person",
                "name": "Max Levinson"
                },
                ],
            "datePublished": "2015-11-10T04:44:44.387671Z"
        }

class ArkDataset():
    ark= {
        "@context": "http://schema.org",
        "@id": "testDatasetGUID",
        "@type": "Dataset",
        "includedInDataCatalog": "testDCGUID",
        "identifier": [
               "ark:/99999/fk4TestDC",
               {
                  "@type": "PropertyValue",
                  "name": "sha-256",
                  "value": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f"
                },

               {
                  "@type": "PropertyValue",
                  "name": "md5",
                  "value": "madeupchecksum"
                }
            ],

        "url": "http://minid.bd2k.org/minid/landingpage/ark:/88120/r8059v",
        "contentUrl": ["aws://all-hands-meeting/minid_v0.1_Nov_2015.pdf" , "gpc://mygpcbucket"],
        "fileFormat": 'pdf',
        "name": "minid dataset",
        "version": "v1",

        "author": {
            "@id": "http://orcid.org/0000-0003-2129-5269",
            "@type": "Person",
            "name": "Max Levinson"},

        "datePublished": "2015-11-10T04:44:44.387671Z"
    }



ark_dc=  { 
            "@context": "http://schema.org",
            "@id": "testDConeAuth",
            "identifier": "testDConeAuth",
            "@type": "DataCatalog",
            "url": "http://example.org",
            "name": "Ark DataCatalog",
            "author": {
                "@id": "http://orcid.org/0000-0003-2129-5269",
                "@type": "Person",
                "name": "Ian Foster"
                },
            "datePublished": "2015-11-10T04:44:44.387671Z"
    }
# post connected arks working
dc_task = postNeoArk.delay(ark_dc)
dc_task.get()
print(dc_task.result)


doi_dc = {
        "@context": "http://schema.org",
        "@type": "DataCatalog",
        "@id": "10.5072/test9999ADifferentName",
        "identifier": "10.5072/test9999ADifferentName",
        "additionalType": "Data dictionary",
        "name": "GTEx Public Files",
        "description": "A data dictionary that describes each variable in the GTEx_v7_Annotations_SubjectPhenotypesDS.txt",
        "author": {
            "@type": "Organization",
            "name": "The GTEx Consortium"
        }, 
        "keywords": "gtex, annotation, phenotype, gene regulation, transcriptomics",
        "datePublished": "2017",
        "version": "v7",
        "url": "https://www.gtexportal.org/home/datasets",
        "contentSize": "5.4 Mb",
        "funder": {
            "@type": "Organization",
            "@id": "doi:/10.13039/100000050",
            "name": "National Heart, Lung, and Blood Institute"
          }
    }

dc_task = postNeoDoi.delay(doi_dc)
dc_task.get()

print(dc_task.result)
#postNeoArk(ark_dataset)

# add authors to dataset
#dataset_guid = ark_dataset.get('@id')
#dataset_author = ark_dataset.get('author')

#if isinstance(dataset_author,dict):
#    author_task = postNeoAuthor.delay(dataset_author, dataset_guid)

#if isinstance(dataset_author,list):
#    author_task = [postNeoAuthor.delay(auth, dataset_guid) for auth in dataset_author]

# add authors to dc
#dc_guid = ark_dc.get('@id')
#dc_author = ark_dc.get('author')

#if isinstance(dc_author,dict):
#    author_task = postNeoAuthor.delay(dc_author, dc_guid)

#if isinstance(dc_author,list):
#    author_task = [postNeoAuthor.delay(auth, dc_guid) for auth in dc_author]


# add downloads to dataset
#urlLocation = ark_dataset.get('contentUrl')[0]
#encrypted_location = encryptUrl(urlLocation)


#fileFormat = ark_dataset.get('fileFormat')
#checksum_list = list(filter(lambda x: isinstance(x,dict), ark_dataset.get('identifier') )) 

#postDownload.delay(encrypted_location, checksum_list, fileFormat, dataset_guid, 'aws')


download_task = getDownloads.delay('testDConeAuth', 'aws')

print(download_task.get())



