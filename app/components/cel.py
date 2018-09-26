############################################################
#                   TASK QUEUE                             #
############################################################
from celery import Celery
import re, requests, os, json

from app.components.models.auth import UserNode
from app.components.models.identifiers import (ArkNode, DoiNode, DataguidRevision, Metadata,
        DataguidNode, Checksum, Download)

from neomodel import config
from os import environ

NEO_PASSWORD = environ.get('NEO_PASSWORD', '')
NEO_URL = environ.get('NEO_URL', '')
config.DATABASE_URL = 'bolt://neo4j:'+ NEO_PASSWORD +'@'+ NEO_URL +':7687'

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')

celery = Celery(
        'cel',
        backend= REDIS_URL,
        broker = REDIS_URL
        )

#######################
#   Expiring Ark Task #
#######################
@celery.task(name='delete_task')
def delete_task(target, user, password):
    response = requests.delete(
        url = target,
        auth = requests.auth.HTTPBasicAuth(user, password)
    )


#######################
#  Dataguid Neo Tasks #
#######################

@celery.task(name='put_dataguid')
def put_dataguid(UserEmail, did, baseId, rev, schemaJson):
    user = UserNode.nodes.get_or_none(email=UserEmail)
    dg = DataguidNode.nodes.get_or_none(guid=did)

    if dg is None:
        dg = DataguidNode(guid=did, baseId=baseId)
        dg.save()


    metadata = Metadata(
            schemaJson = json.dumps(schemaJson),
            )

    metadata.save()

    revision = DataguidRevision(
            rev = rev
            )
    revision.save()

    dg.hasRevision.connect(revision)
    dg.mintedBy.connect(user)


    revision.hasMetadata.connect(metadata)

    # create checksum nodes
    cs_list = list(filter(lambda x: isinstance(x, dict),
        schemaJson.get('identifier')))

    checksums = [
        Checksum(
            Method=cs_elem.get('name'),
            Value=cs_elem.get('value')
            ).save()
        for cs_elem in cs_list]

    for cs_node in checksums:
        revision.hasChecksum.connect(cs_node)

    # create download nodes
    downloads = [
            Download(
                url=dl,
                contentSize=schemaJson.get('contentSize'),
                fileFormat=schemaJson.get('fileFormat')
                ).save()
            for dl in schemaJson.get('contentUrl')]

    for dl_node in downloads:
        revision.hasDownload.connect(dl_node)


    revision.save()
    dg.save()

@celery.task(name='delete_dataguid')
def delete_dataguid(did, rev):
    dg = DataguidNode.nodes.get_or_none(guid=did)
    rev = DataguidRevision.nodes.get_or_none(rev = did)

    if rev is not None:
        for metadata in rev.hasMetadata.all():
            metadata.delete()
        for checksum in rev.hasChecksum.all():
            checksum.delete()
        for download in rev.hasDownload.all():
            download.delete()
        rev.delete()

    if dg is not None:
        dg.delete()


#################
# Ark Neo Tasks #
#################
@celery.task(name='put_ark')
def put_ark(UserEmail, guid, status, schemaJson):
    user = UserNode.nodes.get_or_none(email=UserEmail)

    ark = ArkNode.nodes.get_or_none(guid=guid)

    if ark is None:
        ark = ArkNode(guid=guid, status=status)
        ark.save()

    else:
        # if an existing ark is found delete all old versions
        for metadata in ark.hasMetadata.all():
            metadata.delete()
        for checksum in ark.hasChecksum.all():
            checksum.delete()
        for download in ark.hasDownload.all():
            download.delete()

    metadata = Metadata(
        schemaJson = json.dumps(schemaJson),
        ).save()


    # add checksum
    if schemaJson.get('identifier') is not None:
        cs_list = list(filter(lambda x: isinstance(x, dict),
            schemaJson.get('identifier')))

        if len(cs_list)!=0:
            checksums = [
                Checksum(
                    Method=cs_elem.get('name'),
                    Value=cs_elem.get('value')
                    ).save()
                for cs_elem in cs_list]

            for cs_node in checksums:
                ark.hasChecksum.connect(cs_node)

    # if minid profile with single specified cs and method
    if schemaJson.get('checksum') is not None and \
        schemaJson.get('checksumMethod') is not None:

        cs = Checksum(
            Method = schemaJson.get('checksumMethod'),
            Value = schemaJson.get('checksum')
        ).save()

        ark.hasChecksum.connect(cs)


    # add downloads
    if schemaJson.get('contentUrl') is not None:
        downloads = [
                Download(
                    url=dl,
                    contentSize=schemaJson.get('contentSize'),
                    fileFormat=schemaJson.get('fileFormat')
                    ).save()
                for dl in schemaJson.get('contentUrl')]

        for dl_node in downloads:
            ark.hasDownload.connect(dl_node)

    ark.mintedBy.connect(user)
    ark.hasMetadata.connect(metadata)


@celery.task(name='delete_ark')
def delete_ark(guid):
    ark = ArkNode.nodes.get_or_none(guid=guid)

    if ark is not None:
        for metadata in ark.hasMetadata.all():
            metadata.delete()
        for checksum in ark.hasChecksum.all():
            checksum.delete()
        for download in ark.hasDownload.all():
            download.delete()
        ark.delete()

#################
# Doi Neo Tasks #
#################
@celery.task(name='put_doi')
def put_doi(UserEmail, guid, status, schemaJson):
    user = UserNode.nodes.get_or_none(email=UserEmail)

    doi = DoiNode.nodes.get_or_none(guid=guid)

    if doi is None:
        doi = DoiNode(guid=guid, status=status)
        doi.save()

    else:
        # if an existing doi is found delete all old versions
        for metadata in doi.hasMetadata.all():
            metadata.delete()
        for checksum in doi.hasChecksum.all():
            checksum.delete()
        for download in doi.hasDownload.all():
            download.delete()

    metadata = Metadata(
        schemaJson = json.dumps(schemaJson),
        ).save()


    # add checksum
    if schemaJson.get('identifier') is not None:
        cs_list = list(filter(lambda x: isinstance(x, dict),
            schemaJson.get('identifier')))

        checksums = [
            Checksum(
                Method=cs_elem.get('name'),
                Value=cs_elem.get('value')
                ).save()
            for cs_elem in cs_list]

        for cs_node in checksums:
            doi.hasChecksum.connect(cs_node)


    # add downloads
    downloads = [
            Download(
                url=dl,
                contentSize=schemaJson.get('contentSize'),
                fileFormat=schemaJson.get('fileFormat')
                ).save()
            for dl in schemaJson.get('contentUrl')]

    for dl_node in downloads:
        doi.hasDownload.connect(dl_node)

    doi.mintedBy.connect(user)
    doi.hasMetadata.connect(metadata)


@celery.task(name='delete_doi')
def delete_doi(guid):
    doi = DoiNode.nodes.get_or_none(guid=guid)

    if doi is not None:
        for metadata in doi.hasMetadata.all():
            metadata.delete()
        for checksum in doi.hasChecksum.all():
            checksum.delete()
        for download in doi.hasDownload.all():
            download.delete()
        doi.delete()
