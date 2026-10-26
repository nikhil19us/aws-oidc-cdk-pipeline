from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_ecs_patterns as ecs_patterns
from constructs import Construct


class ServiceStack(Stack):
    """A small Fargate service behind an ALB.

    Deployment safety is built in: the ECS deployment circuit breaker rolls the
    service back automatically if new tasks never become healthy.
    """

    def __init__(self, scope: Construct, id: str, *, stage: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        prod = stage == "prod"

        vpc = ec2.Vpc(
            self,
            "Vpc",
            max_azs=2,
            nat_gateways=2 if prod else 1,  # prod survives an AZ loss, dev stays cheap
        )
        # Reach S3 privately instead of through the NAT gateway.
        vpc.add_gateway_endpoint("S3", service=ec2.GatewayVpcEndpointAwsService.S3)

        cluster = ecs.Cluster(self, "Cluster", vpc=vpc, container_insights_v2=ecs.ContainerInsights.ENABLED)

        service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "Web",
            cluster=cluster,
            cpu=512 if prod else 256,
            memory_limit_mib=1024 if prod else 512,
            desired_count=2 if prod else 1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_registry("public.ecr.aws/nginx/nginx:stable"),
                container_port=80,
            ),
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            min_healthy_percent=100,
            max_healthy_percent=200,
        )

        service.target_group.configure_health_check(
            path="/",
            healthy_threshold_count=2,
            interval=Duration.seconds(15),
        )

        scaling = service.service.auto_scale_task_count(
            min_capacity=2 if prod else 1,
            max_capacity=6 if prod else 2,
        )
        scaling.scale_on_cpu_utilization("Cpu", target_utilization_percent=60)

        CfnOutput(self, "Url", value=f"http://{service.load_balancer.load_balancer_dns_name}")
