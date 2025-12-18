import boto3
import os
from datetime import datetime
from decimal import Decimal

def upload_to_s3(image_path, bucket_name):
    s3 = boto3.client('s3')
    filename = os.path.basename(image_path)
    s3_key = f'rekognition-input/{filename}'
    s3.upload_file(image_path, bucket_name, s3_key)
    return s3_key

def detect_labels(photo, bucket):
    client = boto3.client('rekognition')
    response = client.detect_labels(Image={'S3Object':{'Bucket':bucket, 'Name':photo}}, MaxLabels=10)
    return response

def write_to_dynamodb(filename, labels, table_name, branch):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    timestamp = datetime.utcnow().isoformat() + 'Z'
    
    # Convert float Confidence values to Decimal
    labels_decimal = [
        {'Name': label['Name'], 'Confidence': Decimal(str(label['Confidence']))}
        for label in labels
    ]
    
    table.put_item(
        Item={
            'filename': filename,
            'labels': labels_decimal,
            'timestamp': timestamp,
            'branch': branch,
        }
    )

def main():
    # Get environment variables
    bucket_name = os.environ.get('S3_BUCKET')
    table_name = os.environ.get('DYNAMODB_TABLE')
    branch_name = os.environ.get('BRANCH_NAME')
    
    # Find image file in images/ folder
    images_dir = 'images'
    image_files = [f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
    
    if not image_files:
        print("No images found in images/ folder")
        exit(1)
    
    # Process first image found
    image_filename = image_files[0]
    image_path = os.path.join(images_dir, image_filename)
    
    # Upload to S3
    s3_key = upload_to_s3(image_path, bucket_name)
    print(f"Uploaded {image_filename} to S3 as {s3_key}")
    
    # Detect labels
    response = detect_labels(s3_key, bucket_name)
    
    # Format labels (Name and Confidence only)
    formatted_labels = [
        {'Name': label['Name'], 'Confidence': label['Confidence']}
        for label in response['Labels']
    ]
    
    # Write to DynamoDB
    write_to_dynamodb(s3_key, formatted_labels, table_name, branch_name)
    
    print(f"Successfully processed {image_filename}")
    print(f"Detected {len(formatted_labels)} labels")

if __name__ == "__main__":
    main()