import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app import *
import unittest

class TestRenderLandingPage(unittest.TestCase):

    def setUp(self): 
        self.app = Flask(__name__, template_folder='../templates')

    def tearDown(self):
        pass

    def test_minid_processed(self):
        RawANVL = '_profile: minid\n_target: ark:/99999/fk4r8059v\nminid.created: 2015-11-10 04:44:44.387671\nminid.creator: 0000-0003-2129-5269\nminid.checksum: cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f\nminid.checksumMethod: sha1\nminid.status: ACTIVE\nminid.locations: http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf\nminid.titles: minid: A BD2K Minimal Viable Identifier Pilot v0.1'

        RawPayload = '{"_profile": "minid", "_target": "ark:/99999/fk4r8059v", "minid.created": "2015-11-10 04:44:44.387671", "minid.creator": "0000-0003-2129-5269", "minid.checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f", "minid.checksumMethod":"sha1", "minid.status": "ACTIVE", "minid.locations": "http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf", "minid.titles": "minid: A BD2K Minimal Viable Identifier Pilot v0.1"}'
       
        FinishedPayload = '{ "identifier": "ark:/99999/fk4r8059v", "created": "2015-11-10 04:44:44.387671", "creator": "0000-0003-2129-5269", "checksum": "cacc1abf711425d3c554277a5989df269cefaa906d27f1aaa72205d30224ed5f", "checksumMethod":"sha1","status": "ACTIVE","locations": ["http://bd2k.ini.usc.edu/assets/all-hands-meeting/minid_v0.1_Nov_2015.pdf"], "titles": ["minid: A BD2K Minimal Viable Identifier Pilot v0.1"]}'

        # RawANVL to json
        self.assertEqual(ChompAnvl(RawANVL), json.loads(RawPayload))

        # RawANVL to finished  payload
        supposedlyJSON, responseType =ParseJSONLD(RawANVL, "ark:/99999/fk4r8059v")
        self.assertEqual(supposedlyJSON, json.loads(FinishedPayload))
        self.assertEqual(responseType, "minid")
       
        # does it return templated html as string
        with self.app.app_context():
            rendered = RenderLandingPage(ResponseContent= RawANVL, ID= "ark:/99999/fk4r8059v")
        self.assertIsInstance(rendered, str)


    def test_data_catalogue(self):
        RawANVL = '_profile: NIHdc\nNIHdc.type: DataCatalogue\n_target: https://www.gtexportal.org/home/\nNIHdc.name: GTEx Portal'
        
        RawPayload = '{"_profile": "NIHdc", "NIHdc.type": "DataCatalogue", "_target": "https://www.gtexportal.org/home/", "NIHdc.name": "GTEx Portal"}'
        
        FinishedPayload = '{ "@context" : "http://schema.org", "@id" : "ark:/99999/fk4Gtex", "@type": "DataCatalogue", "identifier": "https://www.gtexportal.org/home/", "name": "GTEx Portal"}'

        self.assertDictEqual(ChompAnvl(RawANVL), json.loads(RawPayload))
        # RawANVL to finished  payload
        supposedlyJSON, responseType =ParseJSONLD(RawANVL, "ark:/99999/fk4Gtex")
        self.assertEqual(supposedlyJSON, json.loads(FinishedPayload))
        self.assertEqual(responseType, "DataCatalogue")
       
        # does it return templated html as string
        with self.app.app_context():
            rendered = RenderLandingPage(ResponseContent= RawANVL, ID= "ark:/99999/fk4Gtex")
        self.assertIsInstance(rendered, str)


    def test_datset_unpublished(self):
        RawANVL = '_target: https://www.gtexportal.org/home/datasets\n_profile: NIHdc\nNIHdc.type: DatasetUnpublished\nNIHdc.includedInDataCatalogue: ark:/99999/fk4Gtex\nNIHdc.dateCreated: 01-29-2018\nNIHdc.distribution: V7'
        RawPayload = '{"_target": "https://www.gtexportal.org/home/datasets", "_profile":"NIHdc","NIHdc.type":"DatasetUnpublished", "NIHdc.includedInDataCatalogue": "ark:/99999/fk4Gtex", "NIHdc.dateCreated": "01-29-2018", "NIHdc.distribution": "V7" }'
        FinishedPayload = '{ "@context": "http://schema.org", "@type": "DatasetUnpublished", "@id": "ark:/99999/fk4GtexData1", "identifier": "https://www.gtexportal.org/home/datasets", "includedInDataCatalogue": "ark:/99999/fk4Gtex", "dateCreated": "01-29-2018", "distribution": "V7"}'
        self.assertDictEqual(ChompAnvl(RawANVL), json.loads(RawPayload))
        # RawANVL to finished  payload
        supposedlyJSON, responseType = ParseJSONLD(RawANVL, "ark:/99999/fk4GtexData1")
        self.assertEqual(supposedlyJSON, json.loads(FinishedPayload))
        self.assertEqual(responseType, "DatasetUnpublished")
       
        # does it return templated html as string
        with self.app.app_context():
            rendered = RenderLandingPage(ResponseContent= RawANVL, ID= "ark:/99999/fk4GtexData1")
        self.assertIsInstance(rendered, str)

    
    def test_dataset_published(self):
        RawANVL = "_target: https://www.gtexportal.org/home/datasets\n_profile: NIHdc\nNIHdc.type: DatasetPublished\nNIHdc.includedInDataCatalogue: ark:/99999/fk4GTEx\nNIHdc.dateCreated: 1-29-2018\nNIHdc.datePublished: 1-29-2018\nNIHdc.distribution: V7\nNIHdc.author: Broad Institute\nNIHdc.name: GTEx Analysis V7 (dbGaP Accession phs000424.v7.p2)\nNIHdc.description: GTEx most up to date analysis\nNIHdc.version: V7\nNIHdc.citation: none\nNIHdc.keywords: none"
        RawPayload = '{ "_target": "https://www.gtexportal.org/home/datasets", "_profile": "NIHdc", "NIHdc.type": "DatasetPublished", "NIHdc.includedInDataCatalogue": "ark:/99999/fk4GTEx", "NIHdc.dateCreated": "1-29-2018", "NIHdc.datePublished": "1-29-2018", "NIHdc.distribution": "V7", "NIHdc.author": "Broad Institute", "NIHdc.name": "GTEx Analysis V7 (dbGaP Accession phs000424.v7.p2)", "NIHdc.description": "GTEx most up to date analysis", "NIHdc.version": "V7", "NIHdc.citation": "none", "NIHdc.keywords": "none"}'
        FinishedPayload = '{ "@context": "http://schema.org", "@type": "DatasetPublished", "@id": "ark:/99999/fk4GTExDataPub1", "identifier": "https://www.gtexportal.org/home/datasets", "includedInDataCatalogue": "ark:/99999/fk4GTEx", "dateCreated": "1-29-2018", "datePublished": "1-29-2018", "distribution": "V7", "author": "Broad Institute", "name": "GTEx Analysis V7 (dbGaP Accession phs000424.v7.p2)", "description": "GTEx most up to date analysis", "keywords": "none", "version": "V7", "citation": "none"}'
        self.assertDictEqual(ChompAnvl(RawANVL), json.loads(RawPayload))
        supposedlyJSON, responseType =ParseJSONLD(RawANVL, "ark:/99999/fk4GTExDataPub1")
        self.assertEqual(supposedlyJSON, json.loads(FinishedPayload))
        self.assertEqual(responseType, "DatasetPublished") 
        with self.app.app_context():
            rendered = RenderLandingPage(ResponseContent= RawANVL, ID= "ark:/99999/fk4GTExDataPub1")
        self.assertIsInstance(rendered, str)

    
    def test_dataset_download(self):
        RawANVL = '_target: https://www.gtexportal.org/home/datasets\n_profile: NIHdc\nNIHdc.type: DatasetDownload\nNIHdc.version: madeup checksum1\nNIHdc.inDataset: madeup checksum1\nNIHdc.inDataset: ark:/99999/fk4GTExDataPub1\nNIHdc.contentSize: 100 bytes'
        RawPayload = '{"_target": "https://www.gtexportal.org/home/datasets","_profile": "NIHdc","NIHdc.type": "DatasetDownload","NIHdc.version": "madeup checksum1","NIHdc.inDataset": "ark:/99999/fk4GTExDataPub1","NIHdc.contentSize": "100 bytes"}'
        FinishedPayload = '{"@context": "http://schema.org","@type": "DatasetDownload","@id": "ark:/99999/fk4GTExDownload1","identifier": "https://www.gtexportal.org/home/datasets","inDataset": "ark:/99999/fk4GTExDataPub1","version": "madeup checksum1","contentSize": "100 bytes"}'
        self.assertDictEqual(ChompAnvl(RawANVL), json.loads(RawPayload))
        supposedlyJSON, responseType =ParseJSONLD(RawANVL, "ark:/99999/fk4GTExDownload1")
        self.assertEqual(supposedlyJSON, json.loads(FinishedPayload))
        self.assertEqual(responseType, "DatasetDownload")

        with self.app.app_context():
            rendered = RenderLandingPage(ResponseContent= RawANVL, ID= "ark:/99999/fk4GTExDownload1")
        self.assertIsInstance(rendered, str)


if __name__ == "__main__":
    unittest.main()

