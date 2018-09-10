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
    __label__ = 'Identifier:Dataguid'
    guid = StringProperty(required=True, unique_index=True)
    baseId = StringProperty(required=True)

    hasRevision = RelationshipTo('DataguidRevision', 'hasRevision')
    mintedBy = RelationshipTo('UserNode', 'mintedBy')


class DataguidRevision(StructuredNode):
    rev = StringProperty(required=True)
    dateCreated = DateTimeProperty(default_now=True)

    hasMetadata = RelationshipTo('Metadata', 'hasMetadata', cardinality = cardinality.One)
    hasChecksum = RelationshipTo('Checksum', 'hasChecksum')
    hasDownload = RelationshipTo('Download', 'hasDownload')


class ArkNode(StructuredNode):
    guid = StringProperty(required=True, unique_index=True)
    status = StringProperty()

    hasMetadata = RelationshipTo('Metadata', 'hasMetadata', cardinality = cardinality.One)
    hasChecksum = RelationshipTo('Checksum', 'hasChecksum')
    hasDownload = RelationshipTo('Download', 'hasDownload')
    mintedBy = RelationshipTo('UserNode', 'mintedBy')



class DoiNode(StructuredNode):
    guid = StringProperty(required=True, unique_index=True)
    status = StringProperty()

    hasMetadata = RelationshipTo('Metadata', 'hasMetadata', cardinality = cardinality.One)
    hasChecksum = RelationshipTo('Checksum', 'hasChecksum')
    hasDownload = RelationshipTo('Download', 'hasDownload')
    mintedBy = RelationshipTo('UserNode', 'mintedBy')


class Metadata(StructuredNode):
    schemaJson = JSONProperty(required=True)


class Checksum(StructuredNode):
    Value = StringProperty(required = True)
    Method = StringProperty(required = True)


class Download(StructuredNode):
    fileFormat = StringProperty()
    url = StringProperty(required = True)
    contentSize = StringProperty()

    CLOUDS = {'Azure': 'Azure', 'Google Public Cloud': 'GPC', 'Amazon Web Services': 'AWS'}
    cloud = StringProperty(choices=CLOUDS)
