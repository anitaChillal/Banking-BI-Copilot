# Banking BI Copilot — CI/CD Setup

## GitHub Actions Workflows

### `deploy.yml` — Production Deploy
Triggers on every push to `main`. Runs three jobs:
1. **Deploy Dashboard** — builds React app, syncs to S3, invalidates CloudFront
2. **Deploy Lambdas** — packages and deploys all 5 Lambda functions
3. **Smoke Test** — verifies dashboard, API, and supervisor Lambda are working

### `pr-checks.yml` — PR Validation
Triggers on every pull request to `main`. Runs:
1. **Build Check** — ensures React app builds successfully
2. **Python Check** — validates Lambda syntax

---

## Setup Instructions

### Step 1 — Create GitHub repository

```powershell
cd C:\Users\anita\banking-bi-copilot
git init
git add .
git commit -m "Initial commit — Banking BI Copilot"
```

Create a new repo at https://github.com/new, then:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/banking-bi-copilot.git
git branch -M main
git push -u origin main
```

### Step 2 — Create IAM user for GitHub Actions

```powershell
# Create deploy user
aws iam create-user --user-name banking-bi-github-actions

# Attach required policies
aws iam attach-user-policy --user-name banking-bi-github-actions --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
aws iam attach-user-policy --user-name banking-bi-github-actions --policy-arn arn:aws:iam::aws:policy/CloudFrontFullAccess
aws iam attach-user-policy --user-name banking-bi-github-actions --policy-arn arn:aws:iam::aws:policy/AWSLambda_FullAccess

# Create access key
aws iam create-access-key --user-name banking-bi-github-actions
```

Save the `AccessKeyId` and `SecretAccessKey` from the output.

### Step 3 — Add secrets to GitHub

Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret

Add these two secrets:
- `AWS_ACCESS_KEY_ID` — from Step 2
- `AWS_SECRET_ACCESS_KEY` — from Step 2

### Step 4 — Test the pipeline

```powershell
# Make a small change and push
echo "# Banking BI Copilot" >> README.md
git add .
git commit -m "Test CI/CD pipeline"
git push
```

Go to GitHub → Actions tab to watch the deployment run.

---

## What happens on each push to main

```
Push to main
    ↓
GitHub Actions triggered
    ↓
    ├── detect changed files
    │       ├── phase4_dashboard_react/* → run deploy-dashboard job
    │       └── phase3_agents/lambda_functions/* → run deploy-lambdas job
    ↓
deploy-dashboard:
    npm ci → npm run build → aws s3 sync → cloudfront invalidation
    ↓
deploy-lambdas:
    zip lambda_functions/ → aws lambda update-function-code (x5)
    ↓
smoke-test:
    curl dashboard → curl API → invoke supervisor Lambda
    ↓
GitHub Step Summary with deployment report
```

## Dashboard URL
https://d2qoiexdp2d54l.cloudfront.net
