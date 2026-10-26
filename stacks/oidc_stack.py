from aws_cdk import CfnOutput, Duration, Stack
from aws_cdk import aws_iam as iam
from constructs import Construct


class GithubOidcStack(Stack):
    """Trust GitHub's OIDC issuer and create one deploy role per environment.

    The trust policy is the control that matters: it only accepts tokens issued
    for this repository and for the named GitHub environments, so a fork or a
    random branch cannot assume the role.
    """

    def __init__(self, scope: Construct, id: str, *, github_repo: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        provider = iam.OpenIdConnectProvider(
            self,
            "GithubProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        for name in ("dev", "prod"):
            role = iam.Role(
                self,
                f"Deploy-{name}",
                role_name=f"github-deploy-{name}",
                max_session_duration=Duration.hours(1),
                assumed_by=iam.WebIdentityPrincipal(
                    provider.open_id_connect_provider_arn,
                    conditions={
                        "StringEquals": {
                            "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                            # Only jobs that run in this GitHub environment (which can
                            # require reviewers) may assume this role.
                            "token.actions.githubusercontent.com:sub": f"repo:{github_repo}:environment:{name}",
                        }
                    },
                ),
            )
            # CDK deploys by assuming its own bootstrap roles. The pipeline role only needs
            # permission to do that, nothing else.
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=["sts:AssumeRole"],
                    resources=[f"arn:aws:iam::{self.account}:role/cdk-*"],
                )
            )
            CfnOutput(self, f"RoleArn-{name}", value=role.role_arn)
