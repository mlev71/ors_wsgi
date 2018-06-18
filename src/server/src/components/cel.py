############################################################
#                   TASK QUEUE                             #
############################################################
from celery import Celery
import re
import requests

celery = Celery(
        'cel',
        backend= 'redis://redis:6379',
        broker = 'redis://redis:6379' 
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



# tasks for uploading to database
@celery.task
def neo_upload_task():
    pass

@celery.task
def neo_delete_task():
    pass



def escape(s):
    return re.sub("[%:\r\n]", lambda c: "%%%02X" % ord(c.group(0)), s)


def outputAnvl(anvlDict):
    ''' Encode all objects into strings, lists into strings
    '''
    return "\n".join("%s: %s" % (escape(str(name)), escape(str(value) )) for name,value in anvlDict.items()).encode('utf-8')


if __name__=="__main__":
    print(delete_task.name)
    print(put_task.name)

