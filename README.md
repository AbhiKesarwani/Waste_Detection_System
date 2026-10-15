# End-to-End Waste Detection Using YOLOv5

An end-to-end computer vision application that uses **YOLOv5** to detect waste in images through a **Flask web interface**. The project brings together an object-detection model, a web application for interacting with predictions, and a containerized deployment workflow for running the application on AWS.

## About the Project

Waste detection can help automate the identification of waste in visual data and support applications such as waste monitoring, sorting, and environmental management. This project provides a web-based interface for submitting images for detection and includes routes for prediction, live-camera detection, and starting the training pipeline.

### Key Features

- **Image-based detection:** Submit an image through the web application for model inference.
- **Live detection route:** Access the live-camera detection interface.
- **Training route:** Trigger the project's training pipeline through the application.
- **Flask application:** Serves the web interface and prediction endpoints.
- **Docker support:** Packages the application for consistent deployment.
- **AWS deployment:** Supports hosting the container on an EC2 instance and storing the image in Amazon ECR. GitHub Actions can optionally automate deployment when configured for the repository.

### Project Workflow

The high-level workflow is:

1. **Configuration and constants** define settings used by the pipeline.
2. **Data ingestion and validation** prepare the data for the training workflow.
3. **Model training** runs the configured YOLOv5 training pipeline.
4. **Model inference** uses the available model weights to detect waste in submitted images or a supported live source.
5. **Flask application** presents the web interface and serves the application's routes.
6. **Container deployment** packages the application with Docker for deployment to AWS.

### Application Routes

| Route | Purpose |
| --- | --- |
| `/` | Web application interface |
| `/predict` | Image prediction endpoint |
| `/live` | Live-camera detection interface |
| `/train` | Starts the training pipeline |

The application listens on port **8080** by default.

### Technology Stack

- **Language:** Python
- **Computer vision / object detection:** YOLOv5, PyTorch
- **Web framework:** Flask
- **Containerization:** Docker
- **Cloud deployment:** Amazon EC2, Amazon Elastic Container Registry (ECR)
- **Optional CI/CD:** GitHub Actions with a self-hosted runner

## AWS Deployment (EC2 + ECR)

This section describes building the Docker image, publishing it to Amazon ECR, and running it on an Ubuntu EC2 instance. Replace all example values with your own AWS resource details. Never commit access keys, registry credentials, or other secrets to this repository.

### Prerequisites

- An AWS account and a selected AWS Region.
- An Amazon ECR repository (for example, `waste-detection`).
- An Ubuntu EC2 instance.
- Docker installed locally for building the image and Docker installed on EC2 for running it.
- AWS CLI installed and configured on the machine used to push the image.
- The project's `Dockerfile`, application files, model weights, and dependencies available as required by the container build.

### 1. Create AWS resources

1. Sign in to the [AWS Management Console](https://console.aws.amazon.com/).
2. Select the AWS Region for the deployment.
3. Create an Amazon ECR repository named `waste-detection` (or choose another name and use it consistently below).
4. Launch an Ubuntu EC2 instance.
5. Configure its security group:
   - Allow **SSH (TCP 22)** only from your trusted IP address.
   - Allow **TCP 8080** only from the client IP ranges that need to access the application.
6. Attach an EC2 IAM instance role that permits pulling images from the chosen ECR repository.

You will need your AWS Region, AWS account ID, ECR repository name, and EC2 public IP or DNS name. These identifiers are not credentials.

### 2. Install Docker on EC2

Connect to the Ubuntu instance over SSH and run:

```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo systemctl enable --now docker
```

Log out and reconnect for the Docker group membership to take effect. Verify the installation:

```bash
docker --version
```

Alternatively, prefix Docker commands with `sudo` rather than adding the user to the Docker group.

### 3. Build and push the image to Amazon ECR

Run these commands from the project root on a machine with Docker and the AWS CLI installed. The configured AWS identity must have permission to push to the ECR repository.

```bash
export AWS_REGION="ap-south-1"
export AWS_ACCOUNT_ID="YOUR_AWS_ACCOUNT_ID"
export ECR_REPOSITORY_NAME="waste-detection"
export ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

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

Change the sample Region and account ID to match your AWS resources. Do not place AWS access keys in these commands or in source files.

### 4. Pull and run the image on EC2

SSH into EC2. The instance should have an IAM role with permission to pull from ECR. Run:

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

Check the container:

```bash
docker ps
docker logs --tail 100 waste
```

Open the application in a browser at:

```text
http://<EC2-PUBLIC-IP>:8080
```

This address works only when the application is running and the EC2 security group and host firewall allow access. For public production use, consider HTTPS through a load balancer or reverse proxy rather than exposing port 8080 directly.

### 5. Optional: Automate deployment with GitHub Actions

GitHub Actions can build the image, push it to ECR, and deploy it to EC2 when changes are pushed to `main`. This requires a compatible workflow under `.github/workflows/` and matching configuration; these steps will not work unless the workflow exists and is correctly configured.

#### Configure a self-hosted runner

1. In the repository, open **Settings → Actions → Runners → New self-hosted runner**.
2. Select **Linux** and follow GitHub's displayed setup commands on the EC2 instance.
3. Keep the runner online with Docker installed. Limit which repositories and workflows can use it, since workflow jobs can execute commands on the runner host.

#### Configure GitHub Actions credentials

Open **Settings → Secrets and variables → Actions** and add only the values required by your workflow. A workflow based on the reference configuration may use these names; verify them against the actual workflow file:

| Secret or variable | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | IAM access key, if static credentials are used |
| `AWS_SECRET_ACCESS_KEY` | Matching IAM secret key, if static credentials are used |
| `AWS_REGION` | AWS Region containing the ECR repository |
| `AWS_ECR_LOGIN_URI` | ECR registry URI, e.g. `123456789012.dkr.ecr.ap-south-1.amazonaws.com` |
| `ECR_REPOSITORY_NAME` | ECR repository name, e.g. `waste-detection` |

Use a dedicated IAM identity with least-privilege permissions. Prefer GitHub OIDC federation with an AWS IAM role over long-lived access keys when the workflow supports it. Never add secret values to README files, workflow files, or source code.

After the workflow is configured, push your changes:

```bash
git add .
git commit -m "Update AWS deployment"
git push origin main
```

Check the repository's **Actions** tab for the workflow result. If it deploys to EC2, verify the container on the instance with `docker ps` and `docker logs waste`.

## Troubleshooting

- **ECR login fails:** Verify the AWS Region, account ID, AWS CLI identity, and ECR permissions.
- **Image push is denied:** Check that the identity used locally has permission to upload layers and images to the repository.
- **EC2 cannot pull the image:** Confirm the EC2 instance role permits ECR pulls and the image exists in the selected Region and repository.
- **The website is unreachable:** Confirm the container is running, port `8080` is mapped, the app listens on `0.0.0.0:8080`, and the security group allows traffic from your client IP.
- **The container exits:** Inspect `docker logs waste` for application errors or missing model files.
- **GitHub blocks a push for a secret:** Remove the credential from every commit in the proposed push and rotate it if it was real. Editing the latest README alone does not remove a secret from earlier commits.

## Security Notes

- Never commit AWS keys, Azure registry keys, passwords, or `.env` files.
- Keep large datasets and generated artifacts out of Git unless they are intentionally part of the project.
- Rotate any credential that was accidentally committed or exposed.
