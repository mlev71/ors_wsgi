import boto3

ecs = boto3.client('ecs')

CLUSTER = 'arn:aws:ecs:us-east-1:280922329489:cluster/ORS_Test'

taskMetadata = ecs.list_tasks(
    cluster = CLUSTER,
    serviceName = 'wsgi_service'
)

response = ecs.stop_task(
        cluster = CLUSTER,
        task = taskMetadata['taskArns'][0]
        )

assert response is not None
