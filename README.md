# aws-oidc-cdk-pipeline

A small reference for shipping to AWS from GitHub Actions without storing AWS keys, with a manual approval before production and an automatic rollback if a release is unhealthy. Written in Python with AWS CDK.

This is a sanitized sample of patterns I use at work. It contains no employer code.

## What it shows

| Concern | How it is handled | Where |
|---|---|---|
| No long-lived keys in CI | GitHub's OIDC token is exchanged for a short-lived IAM role | `stacks/oidc_stack.py`, `.github/workflows/deploy.yml` |
| Who may deploy | Role trust is limited to this repo and a named GitHub environment (`dev`, `prod`) | `stacks/oidc_stack.py` |
| Least privilege | The pipeline role can only assume the CDK bootstrap roles | `stacks/oidc_stack.py` |
| Gated promotion | `dev` deploys on merge, `prod` waits for a reviewer, then shows a `cdk diff` first | `.github/workflows/deploy.yml` |
| Safe releases | ECS deployment circuit breaker rolls back unhealthy tasks | `stacks/service_stack.py` |
| Cost vs resilience | `prod` gets two NAT gateways and two tasks, `dev` gets one of each | `stacks/service_stack.py` |
| Private S3 access | S3 gateway endpoint keeps traffic off the NAT | `stacks/service_stack.py` |
| Reviewable infrastructure | Assertion tests run before anything deploys | `tests/` |

## Flow

```
pull request  ->  pytest + cdk synth
merge to main ->  test -> deploy dev -> (reviewer approves) -> cdk diff -> deploy prod
                          each job assumes its own short-lived role through OIDC
```

## Try it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
npm install -g aws-cdk
cdk synth -c stage=prod -c account=111111111111 -c github_repo=your-org/your-repo
```

## Set it up in your own account

1. Bootstrap CDK in each account: `cdk bootstrap`.
2. Deploy the trust stack once per account: `cdk deploy GithubOidc -c github_repo=your-org/your-repo`.
3. In the GitHub repo, create environments `dev` and `prod`. Add required reviewers to `prod`.
4. Add repository variables: `DEV_DEPLOY_ROLE_ARN`, `PROD_DEPLOY_ROLE_ARN`, `DEV_ACCOUNT_ID`, `PROD_ACCOUNT_ID` (the role ARNs are stack outputs).
5. Push to `main`.

## Design notes and trade-offs

- **Environment in the trust policy, not just the repo.** Tying the role to `environment:prod` means a job only gets the production role after GitHub's approval gate passes. A repo-only condition would let any branch assume it.
- **Approval gates cost minutes.** In exchange, every production change is seen by a person and a `cdk diff` before it ships.
- **Circuit breaker, not a custom script.** ECS already knows when tasks fail to become healthy, so the rollback uses the platform feature instead of something I would have to maintain.
- **Two NAT gateways in prod only.** It is the main cost difference between environments. Dev tolerates an AZ outage, prod does not.
- **The sample uses a public nginx image** so it deploys anywhere. Replace it with an ECR image built in an earlier job.

## License

MIT
