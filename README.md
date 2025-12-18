# AWS Rekognition CI/CD Pipeline

Automated image analysis pipeline using GitHub Actions, AWS Rekognition, and DynamoDB. The pipeline automatically processes images through separate beta and production environments based on branch workflows.

## Architecture Overview

This project implements a dual-environment CI/CD pipeline:

- **Beta Environment**: Triggered on Pull Requests to `main` branch
  - Processes images and writes results to `beta_results` DynamoDB table
  - Allows testing before production deployment

- **Production Environment**: Triggered on merge to `main` branch
  - Processes images and writes results to `prod_results` DynamoDB table
  - Represents production deployment

### Workflow

1. Developer adds image(s) to `images/` folder
2. Creates Pull Request → Beta workflow runs → Results in `beta_results` table
3. After review, PR is merged → Production workflow runs → Results in `prod_results` table

### Technology Stack

- **GitHub Actions**: CI/CD automation
- **AWS S3**: Image storage
- **AWS Rekognition**: Image label detection
- **AWS DynamoDB**: Results storage
- **Python (boto3)**: AWS SDK for automation

## Prerequisites

- AWS Account with appropriate permissions
- GitHub repository
- Basic understanding of AWS services (S3, Rekognition, DynamoDB, IAM)

## AWS Setup

### 1. Create S3 Bucket
```bash
# Via AWS CLI
aws s3 mb s3://your-bucket-name --region us-east-1

# Or use AWS Console:
# - Navigate to S3
# - Click "Create bucket"
# - Enter bucket name
# - Keep default settings
# - Click "Create bucket"
```

**Note**: The script automatically creates a `rekognition-input/` prefix when uploading images.

### 2. Create DynamoDB Tables

Create two tables with identical schemas:

**Table 1: `beta_results`**
```bash
aws dynamodb create-table \
    --table-name beta_results \
    --attribute-definitions AttributeName=filename,AttributeType=S \
    --key-schema AttributeName=filename,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

**Table 2: `prod_results`**
```bash
aws dynamodb create-table \
    --table-name prod_results \
    --attribute-definitions AttributeName=filename,AttributeType=S \
    --key-schema AttributeName=filename,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

**Schema**:
- **Partition Key**: `filename` (String)
- **Attributes**: `labels` (List), `timestamp` (String), `branch` (String)

### 3. Create IAM User and Policy

**Create IAM Policy** (`rekognition-pipeline-policy.json`):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "rekognition:DetectLabels"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/beta_results",
                "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/prod_results"
            ]
        }
    ]
}
```

**Create IAM User**:
```bash
# Create user
aws iam create-user --user-name rekognition-pipeline-user

# Attach policy
aws iam put-user-policy \
    --user-name rekognition-pipeline-user \
    --policy-name RekognitionPipelinePolicy \
    --policy-document file://rekognition-pipeline-policy.json

# Create access keys
aws iam create-access-key --user-name rekognition-pipeline-user
```

Save the `AccessKeyId` and `SecretAccessKey` - you'll need these for GitHub secrets.

## GitHub Configuration

### 1. Add Repository Secrets

Navigate to your repository: **Settings → Secrets and variables → Actions → New repository secret**

Add the following secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | Your AWS access key | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret key | IAM user secret key |
| `AWS_REGION` | `us-east-1` (or your region) | AWS region for services |
| `S3_BUCKET` | Your bucket name | S3 bucket for image storage |

### 2. Workflow Files

The repository includes two GitHub Actions workflows:

- `.github/workflows/on_pull_request.yml` - Beta environment workflow
- `.github/workflows/on_merge.yml` - Production environment workflow

These are pre-configured and will run automatically based on branch events.

## Usage

### Adding Images for Analysis

1. **Add image to repository**:
```bash
   # Place your .jpg, .jpeg, or .png file in the images/ folder
   cp /path/to/your/image.jpg images/
```

2. **Create a branch and Pull Request**:
```bash
   git checkout -b test-image-analysis
   git add images/
   git commit -m "Add test image for analysis"
   git push origin test-image-analysis
```

3. **Create Pull Request on GitHub**:
   - Navigate to your repository
   - Click "Pull requests" → "New pull request"
   - Select your branch → Create PR
   - **Beta workflow will run automatically**

4. **Review Results**:
   - Check GitHub Actions tab for workflow status
   - Query `beta_results` DynamoDB table (see Verification section)

5. **Merge to Production**:
   - If results look good, merge the PR
   - **Production workflow runs automatically**
   - Results written to `prod_results` table

## Verification

### Check Workflow Status

Navigate to **Actions** tab in your GitHub repository to view workflow runs.

### Query DynamoDB Results

**Via AWS Console**:
1. Navigate to DynamoDB
2. Select `beta_results` or `prod_results` table
3. Click "Explore table items"
4. View detected labels for your images

**Via AWS CLI**:
```bash
# Query beta results
aws dynamodb scan --table-name beta_results

# Query prod results
aws dynamodb scan --table-name prod_results

# Query specific image
aws dynamodb get-item \
    --table-name beta_results \
    --key '{"filename": {"S": "rekognition-input/your-image.jpg"}}'
```

**Example Result**:
```json
{
  "filename": "rekognition-input/basketball.jpeg",
  "labels": [
    {"Name": "Basketball", "Confidence": 99.12},
    {"Name": "Sport", "Confidence": 98.45},
    {"Name": "Ball", "Confidence": 97.89}
  ],
  "timestamp": "2025-12-18T16:30:45Z",
  "branch": "final-test"
}
```

## Project Structure
```
2016GSWarriorsLoss/
├── .github/
│   └── workflows/
│       ├── on_pull_request.yml    # Beta environment workflow
│       └── on_merge.yml            # Production environment workflow
├── images/                         # Place images here for analysis
│   └── basketball.jpeg
├── analyze_image.py                # Main Python script
├── .gitignore
└── README.md
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'boto3'`
- **Solution**: Verify workflow includes `pip install boto3` step

**Issue**: `InvalidS3ObjectException: Unable to get object metadata`
- **Solution**: Ensure image is uploaded to S3 before Rekognition call
- Check S3 bucket name in secrets matches actual bucket

**Issue**: `TypeError: Float types are not supported. Use Decimal types instead`
- **Solution**: Ensure confidence values are converted to `Decimal` type before DynamoDB write

**Issue**: Workflow not triggering
- **Solution**: Verify workflow files are in `.github/workflows/` directory
- Check branch names match workflow triggers (`main` branch)

### Viewing Workflow Logs

1. Navigate to **Actions** tab
2. Click on the failed workflow run
3. Click on the failed job
4. Expand steps to view detailed logs

## Cost Considerations

- **S3**: Minimal storage costs for images
- **Rekognition**: Pay per image analyzed (~$0.001 per image)
- **DynamoDB**: On-demand pricing (Pay per request)
- **GitHub Actions**: Free tier includes 2,000 minutes/month

**Estimated cost**: < $1/month for testing purposes

## Future Enhancements

- [ ] Support for batch image processing
- [ ] Add image quality checks before analysis
- [ ] Implement CloudWatch logging
- [ ] Add SNS notifications for workflow completion
- [ ] Create Lambda function alternative to GitHub Actions
- [ ] Add custom label filtering based on confidence threshold

## License

This project is available under the MIT License.

## Author

Granville Barrett
- GitHub: [@gbarrett78](https://github.com/gbarrett78)
- LinkedIn: [Granville Barrett](https://linkedin.com/in/granville-barrett)

---

**Project completed as part of Level Up in Tech (LUIT) Cloud Engineering Program**
