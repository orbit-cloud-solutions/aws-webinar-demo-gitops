from aws_cdk import (
    Duration,
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_iam as iam,
)
from constructs import Construct

class CiCdStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, conf: dict,**kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        s3_upload_policy_statement = iam.PolicyStatement(
                                    sid="WriteSourceS3",
                                    effect=iam.Effect.ALLOW,
                                    actions=[
                                        "s3:PutObject*"
                                    ],
                                    resources=[
                                        "*",
                                    ]
        )
        s3_download_policy_statement = iam.PolicyStatement(
                                    sid="ReadSourceS3",
                                    effect=iam.Effect.ALLOW,
                                    actions=[
                                        "s3:GetBucket*",
                                        "s3:GetObject*",
                                        "s3:List*"
                                    ],
                                    resources=[
                                        "*",
                                    ]
        )

        cf_policy_statement = iam.PolicyStatement(
            sid="CloudFormation",
            effect=iam.Effect.ALLOW,
            actions=[
                "cloudformation:DescribeStack*",
                "cloudformation:GetTemplate",
            ],
            resources=[
                "*",
            ]
        )
        sts_policy_statement = iam.PolicyStatement(
            sid="STS",
            effect=iam.Effect.ALLOW,
            actions=[
                "sts:AssumeRole",
                "iam:PassRole"
            ],
            resources=[
                "arn:aws:iam::" + conf['aws_account'] + ":role/cdk*",
            ]
        )

        ecr_policy_statement = iam.PolicyStatement(
            sid="ECR",
            effect=iam.Effect.ALLOW,
            actions=[
                "ecr:BatchCheckLayerAvailability",
                "ecr:BatchGetImage",
                "ecr:CompleteLayerUpload",
                "ecr:CreateRepository",
                "ecr:DeleteRepository",
                "ecr:DescribeImages",
                "ecr:DescribeRepositories",
                "ecr:GetAuthorizationToken",
                "ecr:GetDownloadUrlForLayer",
                "ecr:InitiateLayerUpload",
                "ecr:ListImages",
                "ecr:PutImage",
                "ecr:PutLifecyclePolicy",
                "ecr:UploadLayerPart",
                "ec2:DescribeAvailabilityZones"
            ],
            resources=[
                "*",
            ]
        )

        source_output = codepipeline.Artifact()

        deploy_project = codebuild.PipelineProject(self, "CodeBuildCdkDeploy",
            project_name=conf["prefix"]+"cdk-deploy",
            build_spec=codebuild.BuildSpec.from_source_filename("cicd/cdk-deploy-buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4, privileged=True
            ),
            timeout=Duration.minutes(20)
        )

        deploy_project.add_to_role_policy(cf_policy_statement)
        deploy_project.add_to_role_policy(sts_policy_statement)
        deploy_project.add_to_role_policy(s3_upload_policy_statement)
        deploy_project.add_to_role_policy(s3_download_policy_statement)
        deploy_project.add_to_role_policy(ecr_policy_statement)

        test_project = codebuild.PipelineProject(self, "CodeBuildTest",
            project_name=conf["prefix"]+"test",
            build_spec=codebuild.BuildSpec.from_source_filename("cicd/test-buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4, privileged=True
            ),
            timeout=Duration.minutes(20)
        )

        destroy_project = codebuild.PipelineProject(self, "CodeBuildCdkDestroyAll",
            project_name=conf["prefix"]+"cdk-destroy-all",
            build_spec=codebuild.BuildSpec.from_source_filename("cicd/cdk-destroy-all-buildspec.yml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.AMAZON_LINUX_2_4, privileged=True
            ),
            timeout=Duration.minutes(20)
        )

        destroy_project.add_to_role_policy(cf_policy_statement)
        destroy_project.add_to_role_policy(sts_policy_statement)
        destroy_project.add_to_role_policy(s3_upload_policy_statement)
        destroy_project.add_to_role_policy(s3_download_policy_statement)
        destroy_project.add_to_role_policy(ecr_policy_statement)


        manual_approve_action=codepipeline_actions.ManualApprovalAction(
            action_name="Approve",
            run_order=1
        )

        for env in conf["env"].keys(): 

            source_action = codepipeline_actions.CodeStarConnectionsSourceAction(
                action_name="Github_Source-"+env,
                owner=conf["github"]["owner"],
                repo=conf["github"]["repo"],
                branch=env,
                output=source_output,
                connection_arn=conf["github"]["codestar-connection"],
            )
        
            deploy_action = codepipeline_actions.CodeBuildAction(
                action_name="Deploy-"+env,
                project=deploy_project,
                input=source_output,
                environment_variables={
                    "ENV": codebuild.BuildEnvironmentVariable(value=env)
                },
            )

            test_action = codepipeline_actions.CodeBuildAction(
                action_name="Test-"+env,
                project=test_project,
                input=source_output,
                environment_variables={
                    "ENV": codebuild.BuildEnvironmentVariable(value=env)
                },
            )

            codepipeline_deploy = codepipeline.Pipeline(self, "DeployCDK-"+env,
                                                pipeline_name=conf["prefix"]+"gitops-deploy-"+env.upper(),
                                                stages=[codepipeline.StageProps(stage_name="Source", actions=[source_action]),
                                                        codepipeline.StageProps(stage_name="Deploy-"+env, actions=[deploy_action]),
                                                        codepipeline.StageProps(stage_name="Test-"+env, actions=[test_action])]
                                                )

            deploy_action = codepipeline_actions.CodeBuildAction(
                action_name="Destroy-"+env,
                project=destroy_project,
                input=source_output,
                environment_variables={
                    "ENV": codebuild.BuildEnvironmentVariable(value=env)
                },
                run_order=2
            )

            codepipeline_destroy = codepipeline.Pipeline(self, "DestroyCDK-"+env,
                                                pipeline_name=conf["prefix"]+"gitops-DESTROY-"+env.upper(),
                                                stages=[codepipeline.StageProps(stage_name="Source", actions=[source_action]),
                                                        codepipeline.StageProps(stage_name="Destroy-"+env, actions=[manual_approve_action,deploy_action])]
                                                )