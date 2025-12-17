import boto3
import os
from datetime import datetime

def upload_to_s3(image_path, bucket_name):
    s3 = boto3.client('s3')

    filename =os.path.basename(image_path)

    s3_key = f'rekognition-input/{filename}'

    s3.upload_file(image_path, bucket_name, s3_key)

    return s3_key

def detect_labels(photo, bucket):
     client = boto3.client('rekognition')

     response = client.detect_labels(Image={'S3Object':{'Bucket':bucket, 'Name':photo}}, MaxLabels=10)

     # Uncomment to use image properties and filtration settings
     #Features=["GENERAL_LABELS", "IMAGE_PROPERTIES"],
     #Settings={"GeneralLabels": {"LabelInclusionFilters":["Cat"]},
     # "ImageProperties": {"MaxDominantColors":10}}


     return response

def write_to_dynamodb(filename, labels, table_name, branch):
     dynamodb = boto3.resource('dynamodb')
     table = dyanmodb.Table(table_name)

     timestamp = datetime.utcnow().isoformat() + 'Z'

     table.put_item(
         Item={
             'filename': filename,
             'labels': labels,
             'timestamp': timestamp,
             'branch': branch,
         }
     )

     print('Detected labels for ' + photo)
     print()
     for label in response['Labels']:
         print("Label: " + label['Name'])
         print("Confidence: " + str(label['Confidence']))
         print("Instances:")

         for instance in label['Instances']:
             print(" Bounding box")
             print(" Top: " + str(instance['BoundingBox']['Top']))
             print(" Left: " + str(instance['BoundingBox']['Left']))
             print(" Width: " + str(instance['BoundingBox']['Width']))
             print(" Height: " + str(instance['BoundingBox']['Height']))
             print(" Confidence: " + str(instance['Confidence']))
             print()

         print("Parents:")
         for parent in label['Parents']:
            print(" " + parent['Name'])

         print("Aliases:")
         for alias in label['Aliases']:
             print(" " + alias['Name'])

             print("Categories:")
         for category in label['Categories']:
             print(" " + category['Name'])
             print("----------")
             print()

     if "ImageProperties" in str(response):
         print("Background:")
         print(response["ImageProperties"]["Background"])
         print()
         print("Foreground:")
         print(response["ImageProperties"]["Foreground"])
         print()
         print("Quality:")
         print(response["ImageProperties"]["Quality"])
         print()

     return len(response['Labels'])

def main():
    photo = 'photo-name'
    bucket = 'amzn-s3-demo-bucket'
    label_count = detect_labels(photo, bucket)
    print("Labels detected: " + str(label_count))

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    # Get environment variables
    bucket_name = os.environ.get('S3_BUCKET')
    table_name = os.environ.get('DYNAMODB_TABLE')
    branch_name = os.environ.get('BRANCH_NAME')
    
    # Find image file in images/ folder
    images_dir = 'images'
    image_files = [f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.png'))]
    
    if not image_files:
        print("No images found in images/ folder")
        exit(1)
    
    # Process first image found
    image_filename = image_files[0]
    image_path = os.path.join(images_dir, image_filename)
    
    # Upload to S3
    s3_key = upload_to_s3(image_path, bucket_name)
    
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