import json
import boto3
import os
import pandas as pd
from urllib.parse import unquote_plus

s3 = boto3.client('s3')

# Define expected columns
REQUIRED_COLUMNS = ["CargoID", "Weight", "Origin", "Destination"]

def validate_file(file_path, file_type):
    try:
        if file_type.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_type.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        else:
            return False, "Unsupported file type"

        if all(col in df.columns for col in REQUIRED_COLUMNS):
            return True, "Valid file"
        else:
            return False, "Missing required columns"
    except Exception as e:
        return False, str(e)

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))
    
    for record in event['Records']:
        source_bucket = record['s3']['bucket']['name']
        object_key = unquote_plus(record['s3']['object']['key'])
        filename = os.path.basename(object_key)
        file_type = filename.lower()

        download_path = f"/tmp/{filename}"

        try:
            # Download file
            s3.download_file(source_bucket, object_key, download_path)

            # Validate
            is_valid, message = validate_file(download_path, file_type)

            if is_valid:
                destination_bucket = "s3-cargo-processing"
                copy_source = {'Bucket': source_bucket, 'Key': object_key}
                s3.copy_object(CopySource=copy_source, Bucket=destination_bucket, Key=object_key)
                s3.delete_object(Bucket=source_bucket, Key=object_key)
                print(f"{filename} validated and moved to {destination_bucket}")
            else:
                print(f"Validation failed for {filename}: {message}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

    return {
        'statusCode': 200,
        'body': json.dumps('File processing completed.')
    }
