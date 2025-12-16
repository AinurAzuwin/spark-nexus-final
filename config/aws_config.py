# DynamoDB connection

import boto3
import os

def get_dynamodb():
    return boto3.resource(
        "dynamodb",
        region_name="ap-southeast-1",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("AWS_SECRET_KEY")
    )
