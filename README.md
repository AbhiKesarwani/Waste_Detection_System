# End-to-End Waste Detection Using YOLOv5

## AWS Deployment

This guide describes deploying the Flask-based waste detection application on an Ubuntu Amazon EC2 instance using Docker and Amazon Elastic Container Registry (ECR). It also covers an optional GitHub Actions deployment flow using a self-hosted runner.

The application listens on port `8080` by default.

## Prerequisites

- An AWS account and an AWS Region selected for the deployment.
- An Amazon ECR repository (for example, `waste-detection`).
- An Ubuntu EC2 instance.
- Docker installed on the EC2 instance.
- The project Dockerfile and application files available in this repository.

Do not commit AWS access keys, registry credentials, or other secrets to the repository. If a credential has been exposed, revoke or rotate it before deployment.

## 1. Create AWS resources

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/).
2. Select the Region you intend to use.
3. Create an Amazon ECR repository, such as `waste-detection`.
4. Launch an Ubuntu EC2 instance.
5. Configure the instance's security group to allow:
   - **SSH (TCP 22):** only from your trusted IP address.
   - **Application (TCP 8080):** only from the IP ranges that need to access the app. Avoid opening this port to the whole internet unless that is intentional.
6. Attach an EC2 IAM instance role with permission to pull images from the selected ECR repository. This is recommended for manual deployments from EC2.

Keep these values handy; they are identifiers, not secrets:

- AWS Region, such as `ap-south-1`
- AWS account ID
- ECR repository name, such as `waste-detection`
- EC2 public IP address or DNS name

## 2. Install Docker on EC2

Connect to your Ubuntu instance over SSH, then run:

```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
```

Log out and reconnect so the Docker group membership takes effect. Then verify the installation:

```bash
docker --version
sudo systemctl enable --now docker
```

If you prefer not to grant the `ubuntu` user access to Docker, use `sudo docker` for Docker commands instead.

## 3. Build and push the image to Amazon ECR

Run these commands in the project directory on a machine with Docker and the AWS CLI installed and configured with an IAM identity permitted to push to the ECR repository.

Set the values for your deployment:

```bash
export AWS_REGION="ap-south-1"
export AWS_ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"
export ECR_REPOSITORY_NAME="waste-detection"
export ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
```

Authenticate to ECR, create the repository if it does not already exist, then build and push the image:

```bash
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_URI"

aws ecr describe-repositories \
  --repository-names "$ECR_REPOSITORY_NAME" \
  --region "$AWS_REGION" >/dev/null 2>&1 \
  || aws ecr create-repository \
       --repository-name "$ECR_REPOSITORY_NAME" \
       --region "$AWS_REGION"

docker build -t waste-detection .
docker tag waste-detection:latest "${ECR_URI}/${ECR_REPOSITORY_NAME}:latest"
docker push "${ECR_URI}/${ECR_REPOSITORY_NAME}:latest"
```

Replace the example Region and account ID with your own. Do not put access keys in these commands or commit them to a file. Prefer short-lived credentials or an AWS role where possible.

## 4. Pull and run the image on EC2

SSH into EC2. If the instance has the appropriate IAM role attached, authenticate Docker to ECR and run the image:

```bash
export AWS_REGION="ap-south-1"
export AWS_ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"
export ECR_REPOSITORY_NAME="waste-detection"
export ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_URI"

docker pull "${ECR_URI}/${ECR_REPOSITORY_NAME}:latest"
docker rm -f waste 2>/dev/null || true
docker run -d \
  --restart unless-stopped \
  -p 8080:8080 \
  --name waste \
  "${ECR_URI}/${ECR_REPOSITORY_NAME}:latest"
```

Check the container status and logs:

```bash
docker ps
docker logs --tail 100 waste
```

Open the application at:

```text
http://<EC2-PUBLIC-IP>:8080
```

The URL is reachable only if the instance's security group and host firewall allow the traffic. For a public-facing production deployment, use HTTPS through a load balancer or reverse proxy rather than exposing an application port directly.

## 5. Optional: Deploy automatically with GitHub Actions

An automated workflow can build the Docker image, push it to ECR, and deploy it on EC2 when changes are pushed to `main`. This requires a matching workflow file in `.github/workflows/` and correct runner and IAM configuration; these steps will not work unless the workflow is present and configured for this repository.

### Configure EC2 as a self-hosted runner

1. In the GitHub repository, open **Settings → Actions → Runners → New self-hosted runner**.
2. Select **Linux** and follow the commands provided by GitHub on the EC2 instance.
3. Keep the runner online and ensure Docker is installed. Restrict which repositories and workflows can use this runner, because jobs can execute commands on the EC2 host.

### Configure GitHub Actions credentials

Open **Settings → Secrets and variables → Actions** and configure the values expected by your workflow. The reference workflow may use the following names; verify that they match the actual workflow file:

| Name | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | IAM access key for workflow authentication, if using static credentials |
| `AWS_SECRET_ACCESS_KEY` | Corresponding IAM secret key, if using static credentials |
| `AWS_REGION` | AWS Region containing the ECR repository |
| `AWS_ECR_LOGIN_URI` | Registry URI, such as `123456789012.dkr.ecr.ap-south-1.amazonaws.com` |
| `ECR_REPOSITORY_NAME` | ECR repository name, such as `waste-detection` |

Use a dedicated IAM identity with only the permissions the workflow needs. Prefer GitHub OIDC federation with an AWS IAM role over long-lived access keys when the workflow is configured to support it. Never paste secret values into `README.md`, workflow files, source code, or commit history.

Once the workflow is configured, commit and push the deployment changes:

```bash
git add .
git commit -m "Update AWS deployment"
git push origin main
```

Check the **Actions** tab in GitHub to confirm whether the workflow completed successfully. If the workflow runs the container on EC2, verify the running service with `docker ps` and `docker logs waste` on that instance.

## Troubleshooting

- **ECR authentication fails:** confirm the AWS Region, account ID, IAM permissions, and ECR repository URI.
- **Image pull is denied:** make sure the EC2 instance role permits ECR image pulls and that the image exists in the selected repository.
- **The site is unreachable:** confirm the container is running, port `8080` is mapped, the app listens on `0.0.0.0:8080`, and the security group permits access from your client IP.
- **The container exits:** inspect `docker logs waste` for application or model-file errors.
- **GitHub blocks a push for a secret:** remove the credential from every commit in the proposed push and rotate the exposed credential. Editing the latest file alone may not remove a secret from earlier commits.
