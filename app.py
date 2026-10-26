#!/usr/bin/env python3
"""Entry point. Pick the stage with `-c stage=dev|prod` (default: dev)."""
import aws_cdk as cdk

from stacks.oidc_stack import GithubOidcStack
from stacks.service_stack import ServiceStack

app = cdk.App()
stage = app.node.try_get_context("stage") or "dev"

env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "us-east-1",
)

# One-time, per account: lets GitHub Actions assume a role without stored keys.
GithubOidcStack(
    app,
    "GithubOidc",
    github_repo=app.node.try_get_context("github_repo") or "your-org/your-repo",
    env=env,
)

ServiceStack(app, f"Service-{stage}", stage=stage, env=env)

app.synth()
