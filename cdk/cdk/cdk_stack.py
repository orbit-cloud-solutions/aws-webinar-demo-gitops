from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as targets,
    aws_elasticloadbalancingv2_actions as actions,
    aws_route53 as route53,
    aws_route53_targets as route53_targets,
)
import aws_cdk as cdk
from constructs import Construct

class CdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, conf: dict, app_env: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ecr_repo_uri=conf["aws_account"]+".dkr.ecr."+conf["aws_region"]+".amazonaws.com/"+conf["ecr_repo_name"]
        prefix=conf["prefix"]
        cpu_size=conf["env"][app_env]["cpu_size"]
        memory_size=conf["env"][app_env]["memory_size"]


        vpc = ec2.Vpc.from_lookup(self, "VPC",
            is_default=True
        )

        cluster = ecs.Cluster(self, prefix+"-"+ app_env,
            cluster_name=prefix+ app_env,
            vpc=vpc
        )

        ecs_execution_role = iam.Role(
            scope=self,
            id='CoreECSExecutionRole',
            role_name=prefix+"FargateContainerRole"+app_env,
            managed_policies=[iam.ManagedPolicy.from_managed_policy_arn(
                scope=self,
                id='AmazonECSTaskExecutionRolePolicy',
                managed_policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
            )],
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("ecs.amazonaws.com"),
                iam.ServicePrincipal("ecs-tasks.amazonaws.com")
            )
        )

        target_groups={}

        for deployment in conf['env'][app_env]['deployments']:            

            logDetail = logs.LogGroup(self, prefix+app_env+"-"+deployment["name"]+"LogGroup", log_group_name="/"+prefix+"ecs-service-"+app_env+"-"+deployment["name"], retention=logs.RetentionDays.ONE_DAY, removal_policy=cdk.RemovalPolicy.DESTROY)

            fargate_task_definition = ecs.FargateTaskDefinition(self, prefix+app_env+"-"+deployment["name"]+"TD",
                family=prefix+app_env+"-"+deployment["name"],
                memory_limit_mib=int(memory_size),
                cpu=int(cpu_size),
                execution_role=ecs_execution_role,
                task_role=ecs_execution_role
            )
            fargate_task_definition.add_container(prefix+app_env+"-"+deployment["name"],
                image=ecs.ContainerImage.from_registry(ecr_repo_uri+":"+deployment["version"]),
                logging=ecs.LogDriver.aws_logs(stream_prefix = deployment["name"], log_group=logDetail),
                port_mappings=[ecs.PortMapping(container_port = 8080)],
                environment={"BACKGROUND_COLOR":deployment["name"]}
            )

            service = ecs.FargateService(self, prefix+app_env+"-"+deployment["name"]+"service",
                cluster=cluster,
                task_definition=fargate_task_definition,
                desired_count=1,
                service_name=prefix+app_env+"-"+deployment["name"],
                assign_public_ip=True
            )

            applicationTargetGroup = elbv2.ApplicationTargetGroup(self, prefix+app_env+"-"+deployment["name"]+"TG", 
                target_type=elbv2.TargetType.IP,
                target_group_name=prefix+"ecs-"+app_env+"-"+deployment["name"],
                protocol=elbv2.ApplicationProtocol.HTTP,
                port=80,
                vpc=vpc,
                health_check=elbv2.HealthCheck(
                                path="/",
                                healthy_http_codes="200",
                                healthy_threshold_count=2,
                                interval=Duration.seconds(5),
                                timeout=Duration.seconds(2),
                                )
            )

            service.attach_to_application_target_group(
                target_group=applicationTargetGroup
            )

            target_groups[deployment["name"]]=applicationTargetGroup
        
        alb=elbv2.ApplicationLoadBalancer(
            self,
            "ElasticLoadBalancer",
            vpc=vpc,
            load_balancer_name=prefix+app_env,
            internet_facing=True,
        )
               
        listener_actions=[]
        
        # prepare configuration for weighted routing
        for deployment in conf['env'][app_env]['deployments']: 
            listener_action={
                "weight": deployment["weight"],
                "targetGroup": target_groups[deployment["name"]]
            }
            listener_actions.append(listener_action)

        alb.add_redirect(
            source_protocol=elbv2.ApplicationProtocol.HTTP,
            source_port=80,
            target_protocol=elbv2.ApplicationProtocol.HTTPS,
            target_port=443,
        )

        https_listener = alb.add_listener(
            "Listener",
            port=443,
            open=True,
            default_action=elbv2.ListenerAction.weighted_forward(listener_actions),
            certificates=[elbv2.ListenerCertificate.from_arn(conf["acm_certificate_arn"])],
            protocol=elbv2.ApplicationProtocol.HTTPS,
        )

        zone = route53.HostedZone.from_hosted_zone_attributes(
            self,
            "existing-zone",
            hosted_zone_id=conf["r53_zone_id"],
            zone_name=conf["r53_zone_name"],
        )

        main_record=route53.ARecord(
            self,
            "AliasRecord",
            record_name=app_env+"."+conf["r53_zone_name"],
            target=route53.RecordTarget(
                alias_target=route53_targets.LoadBalancerTarget(alb)
            ),
            zone=zone,
        )

        CfnOutput(
            self, "MainURL",
            value=main_record.domain_name,
            description="Main URL:"
        )

        # prepare enpoint for individual deployments 
        rule_priority=0
        for deployment in conf['env'][app_env]['deployments']: 
            deployment_record=route53.ARecord(
                self,
                "AliasRecord"+deployment["name"],
                record_name=deployment["name"]+"-"+app_env+"."+conf["r53_zone_name"],
                target=route53.RecordTarget(
                    alias_target=route53_targets.LoadBalancerTarget(alb)
                ),
                zone=zone,
            )

            CfnOutput(
                self, "DeploymentURL"+deployment["name"],
                value=deployment_record.domain_name,
                description="Deployment URL: "+deployment["name"]
            )

            rule_priority=rule_priority+1

            application_listener_rule = elbv2.ApplicationListenerRule(self, "Deployment"+deployment["name"],
                listener=https_listener,
                priority=rule_priority,

                conditions=[
                    elbv2.ListenerCondition.host_headers([deployment_record.domain_name,])
                ],

                action=elbv2.ListenerAction.forward([target_groups[deployment["name"]]])
            )


