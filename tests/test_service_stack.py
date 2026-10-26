import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from stacks.oidc_stack import GithubOidcStack
from stacks.service_stack import ServiceStack

ENV = cdk.Environment(account="111111111111", region="us-east-1")


def service(stage: str) -> Template:
    app = cdk.App()
    return Template.from_stack(ServiceStack(app, f"S-{stage}", stage=stage, env=ENV))


def test_circuit_breaker_rolls_back():
    service("dev").has_resource_properties(
        "AWS::ECS::Service",
        {"DeploymentConfiguration": Match.object_like({"DeploymentCircuitBreaker": {"Enable": True, "Rollback": True}})},
    )


def test_prod_runs_two_tasks_and_two_nat_gateways():
    t = service("prod")
    t.has_resource_properties("AWS::ECS::Service", {"DesiredCount": 2})
    t.resource_count_is("AWS::EC2::NatGateway", 2)


def test_dev_is_cheaper():
    service("dev").resource_count_is("AWS::EC2::NatGateway", 1)


def test_oidc_role_is_locked_to_repo_and_environment():
    app = cdk.App()
    t = Template.from_stack(GithubOidcStack(app, "O", github_repo="acme/platform", env=ENV))
    t.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": Match.object_like(
                {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Condition": {
                                        "StringEquals": Match.object_like(
                                            {"token.actions.githubusercontent.com:sub": "repo:acme/platform:environment:prod"}
                                        )
                                    }
                                }
                            )
                        ]
                    )
                }
            )
        },
    )
