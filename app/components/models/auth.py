from neomodel import (StructuredNode, EmailProperty, StringProperty, JSONProperty, ArrayProperty,
                      DateTimeProperty, RelationshipTo, RelationshipFrom, install_labels, cardinality)
import datetime, base64, json


class TeamNode(StructuredNode):
    __label__ = 'Team:Organization'
    element = StringProperty(required=True)
    kc = StringProperty(required=True)


class UserNode(StructuredNode):
    __label__ = 'User'
    email = EmailProperty(unique_index=True, required=True)
    firstName = StringProperty(required=True)
    lastName = StringProperty(required=True) 

    team = RelationshipTo('TeamNode', 'memberOf', cardinality=cardinality.ZeroOrOne)
    token = RelationshipTo('GlobusLoginNode', 'auth', cardinality=cardinality.ZeroOrOne)


class GlobusLoginNode(StructuredNode):
    __label__ = 'GlobusLoginToken'
    refreshToken = StringProperty(required=True, unique_index = True)
    accessToken = StringProperty(required=True)

    inspected = RelationshipTo('InspectedTokenNode', 'details', cardinality=cardinality.ZeroOrOne)
    authenticates = RelationshipTo('UserNode', 'authFor', cardinality=cardinality.ZeroOrOne)
    identities = RelationshipTo('GlobusIdentityNode', 'identity')
    

class InspectedTokenNode(StructuredNode): 
    __label__= 'TokenDetails'
    email = EmailProperty(required=True, unique_index = True)
    name = StringProperty(required=True)
    username = StringProperty(required=True)
    
    exp = DateTimeProperty(required=True)
    iat = DateTimeProperty(required=True)
 
    identitiesSet = ArrayProperty() 
    login = RelationshipTo('GlobusLoginNode', 'detailsFor')



class GlobusIdentityNode(StructuredNode):
    __label__ = 'GlobusIdentity'
    email = EmailProperty()
    globusId = StringProperty()
    name = StringProperty()
    organization = StringProperty()
    username = StringProperty()    
    login = RelationshipTo('GlobusLoginNode', 'identityFrom')    

