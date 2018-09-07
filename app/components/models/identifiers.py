from neomodel import config
from app.components.models.auth import UserNode


from neomodel import (config, cardinality,
        UniqueIdProperty, StructuredNode, EmailProperty,
                      StringProperty, JSONProperty, ArrayProperty,
                      DateTimeProperty, RelationshipTo, RelationshipFrom, install_labels)


############################
#  Neomodel representation #
############################

class DataguidNode(StructuredNode):
    __label__ = 'Dataguid'
    guid = StringProperty(required=True)
    baseId = StringProperty(required=True)

    hasRevision = RelationshipTo('DataguidRevision', 'hasRevision')
    mintedBy = RelationshipTo('UserNode', 'mintedBy')


class DataguidRevision(StructuredNode):
    rev = StringProperty(required=True)
    dateCreated = DateTimeProperty(default_now=True)

    hasMetadata = RelationshipTo('DataguidMetadata', 'hasMetadata', cardinality = cardinality.One)
    hasChecksum = RelationshipTo('Checksum', 'hasChecksum')
    hasDownload = RelationshipTo('Download', 'hasDownload')


class ArkNode(StructuredNode):
    __label__ = 'Identifier:Ark'
    guid = StringProperty(required=True)

    hasMetadata = RelationshipTo('Metadata', 'hasMetadata', cardinality = cardinality.One)
    hasChecksum = RelationshipTo('Checksum', 'hasChecksum')
    hasDownload = RelationshipTo('Download', 'hasDownload')
    mintedBy = RelationshipTo('UserNode', 'mintedBy')



class DoiNode(StructuredNode):
    __label__ = 'Identifier:Doi'
    guid = StringProperty(required=True)

    hasMetadata = RelationshipTo('Metadata', 'hasMetadata', cardinality = cardinality.One)
    hasChecksum = RelationshipTo('Checksum', 'hasChecksum')
    hasDownload = RelationshipTo('Download', 'hasDownload')
    mintedBy = RelationshipTo('UserNode', 'mintedBy')


class DataguidMetadata(StructuredNode):
    __label__ = 'Metadata'
    schemaJson = JSONProperty(required=True)
    dgJson = JSONProperty(required=True)



class Checksum(StructuredNode):
    Value = StringProperty(required = True)
    Method = StringProperty(required = True)


class Download(StructuredNode):
    fileFormat = StringProperty()
    url = StringProperty(required = True)
    contentSize = StringProperty()
     
    CLOUDS = {'Azure': 'Azure', 'Google Public Cloud': 'GPC', 'Amazon Web Services': 'AWS'}
    cloud = StringProperty(choices=CLOUDS)





