#!/usr/bin/env bash
# One-time AWS setup (default VPC, no load balancer, no NAT gateway = cheapest).
set -euo pipefail
REGION=${REGION:-ap-south-1}
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
MYIP=$(curl -s https://checkip.amazonaws.com)

aws ecr create-repository --repository-name recruiter-agent --region $REGION >/dev/null || true
aws logs create-log-group --log-group-name /ecs/recruiter-agent --region $REGION || true
aws ecs create-cluster --cluster-name recruiter-cluster --region $REGION >/dev/null

cat > /tmp/trust.json <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
aws iam create-role --role-name recruiterAgentExecRole --assume-role-policy-document file:///tmp/trust.json >/dev/null || true
aws iam attach-role-policy --role-name recruiterAgentExecRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
cat > /tmp/ssm.json <<EOF
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":"ssm:GetParameters","Resource":"arn:aws:ssm:$REGION:$ACCOUNT:parameter/recruiter-agent/*"}]}
EOF
aws iam put-role-policy --role-name recruiterAgentExecRole --policy-name ssm-read --policy-document file:///tmp/ssm.json

# Google service-account key -> SSM Parameter Store (SecureString is free; Secrets Manager is not)
aws ssm put-parameter --name /recruiter-agent/google-sa --type SecureString \
  --value file://secrets/sa.json --overwrite --region $REGION >/dev/null

VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text --region $REGION)
SG=$(aws ec2 create-security-group --group-name recruiter-agent-sg --description "recruiter agent" \
  --vpc-id $VPC --query GroupId --output text --region $REGION)
aws ec2 authorize-security-group-ingress --group-id $SG --protocol tcp --port 8000 --cidr $MYIP/32 --region $REGION >/dev/null
echo "Done. ACCOUNT=$ACCOUNT  SG=$SG  (port 8000 open only to $MYIP)"
