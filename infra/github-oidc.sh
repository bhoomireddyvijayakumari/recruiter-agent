#!/usr/bin/env bash
# Usage: ./infra/github-oidc.sh GITHUB_USER/REPO   (lets GitHub Actions deploy without stored AWS keys)
set -euo pipefail
REPO=$1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
aws iam create-open-id-connect-provider --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1 || true
cat > /tmp/gh-trust.json <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Federated":"arn:aws:iam::$ACCOUNT:oidc-provider/token.actions.githubusercontent.com"},"Action":"sts:AssumeRoleWithWebIdentity","Condition":{"StringEquals":{"token.actions.githubusercontent.com:aud":"sts.amazonaws.com"},"StringLike":{"token.actions.githubusercontent.com:sub":"repo:$REPO:ref:refs/heads/main"}}}]}
EOF
aws iam create-role --role-name recruiterAgentGithubRole --assume-role-policy-document file:///tmp/gh-trust.json
aws iam attach-role-policy --role-name recruiterAgentGithubRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser
cat > /tmp/gh-ecs.json <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["ecs:RegisterTaskDefinition","ecs:DescribeTaskDefinition","ecs:DescribeServices","ecs:UpdateService"],"Resource":"*"},{"Effect":"Allow","Action":"iam:PassRole","Resource":"arn:aws:iam::$ACCOUNT:role/recruiterAgentExecRole"}]}
EOF
aws iam put-role-policy --role-name recruiterAgentGithubRole --policy-name ecs-deploy --policy-document file:///tmp/gh-ecs.json
echo "Add GitHub repo secret AWS_ROLE_ARN = arn:aws:iam::$ACCOUNT:role/recruiterAgentGithubRole"
