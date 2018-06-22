cluster_arn="arn:aws:ecs:us-east-1:280922329489:cluster/ORS_Test"
task_arn=`aws ecs list-tasks --cluster ${cluster_arn} --service-name wsgi_service | jq '.taskArns[0]'`
echo ${task_arn}
aws ecs describe-tasks --cluster ${cluster_arn} --tasks `aws ecs list-tasks --cluster ${cluster_arn} --service-name wsgi_service | jq '.taskArns[0]'`
 
#ip= `aws ecs describe-tasks --cluster ${cluster_arn} --tasks ${task_arn} | jq '.tasks[0].containers.networkInterfaces'`
#echo ${ip}
