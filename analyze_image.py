import argparse
import os
from datetime import datetime

import boto3


def upload_to_s3(image_path: str, bucket_name: str, prefix: str = "rekognition-input") -> str:
    """
    Uploads a local image file to S3 and returns the S3 object key.
    """
    s3 = boto3.client("s3")

    filename = os.path.basename(image_path)
    s3_key = f"{prefix}/{filename}"

    s3.upload_file(image_path, bucket_name, s3_key)
    return s3_key


def detect_labels(s3_key: str, bucket_name: str, max_labels: int = 10) -> dict:
    """
    Calls AWS Rekognition DetectLabels on an S3 object and returns the full response.
    """
    client = boto3.client("rekognition")

    response = client.detect_labels(
        Image={"S3Object": {"Bucket": bucket_name, "Name": s3_key}},
        MaxLabels=max_labels,
    )
    return response


def format_labels(rekognition_response: dict) -> list[dict]:
    """
    Reduce Rekognition response to only Name + Confidence for each label.
    """
    labels = rekognition_response.get("Labels", [])
    return [{"Name": l.get("Name"), "Confidence": float(l.get("Confidence", 0.0))} for l in labels]


def write_to_dynamodb(filename: str, labels: list[dict], table_name: str, branch: str) -> None:
    """
    Writes the results to DynamoDB.
    """
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    timestamp = datetime.utcnow().isoformat() + "Z"

    table.put_item(
        Item={
            "filename": filename,
            "labels": labels,
            "timestamp": timestamp,
            "branch": branch,
        }
    )


def find_first_image(images_dir: str = "images") -> str:
    """
    Finds the first .jpg/.jpeg/.png file in the images directory.
    """
    if not os.path.isdir(images_dir):
        raise FileNotFoundError(f"Images directory not found: {images_dir}")

    image_files = [
        f for f in os.listdir(images_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not image_files:
        raise FileNotFoundError(f"No images found in {images_dir}/ (expected .jpg/.jpeg/.png)")

    image_files.sort()
    return os.path.join(images_dir, image_files[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload image -> Rekognition labels -> write to DynamoDB")
    parser.add_argument("--output-table", required=True, help="DynamoDB table name to write results to")
    parser.add_argument("--images-dir", default="images", help="Directory containing images")
    parser.add_argument("--max-labels", type=int, default=10, help="Max labels to request from Rekognition")
    args = parser.parse_args()

    # Required env var (set in GitHub Actions)
    bucket_name = os.environ.get("S3_BUCKET")
    if not bucket_name:
        raise EnvironmentError("Missing required env var: S3_BUCKET")

    # Optional env var
    branch_name = os.environ.get("BRANCH_NAME", "unknown")

    # 1) Find a local image
    image_path = find_first_image(args.images_dir)
    image_filename = os.path.basename(image_path)

    # 2) Upload to S3
    s3_key = upload_to_s3(image_path, bucket_name)

    # 3) Detect labels
    response = detect_labels(s3_key, bucket_name, max_labels=args.max_labels)
    labels = format_labels(response)

    # 4) Write to DynamoDB
    write_to_dynamodb(
        filename=image_filename,
        labels=labels,
        table_name=args.output_table,
        branch=branch_name,
    )

    print(f"Successfully processed {image_filename}")
    print(f"S3: s3://{bucket_name}/{s3_key}")
    print(f"Labels written to DynamoDB table: {args.output_table}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
