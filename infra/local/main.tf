terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.1"
    }
  }
}


provider "aws" {
  access_key                  = "test"
  secret_key                  = "test"
  region                      = "us-west-1" 
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  endpoints {
    apigateway     = "http://localhost:4566"
    cloudformation = "http://localhost:4566"
    cloudwatch     = "http://localhost:4566"
    dynamodb       = "http://localhost:4566"
    ec2            = "http://localhost:4566"
    iam            = "http://localhost:4566"
    kinesis        = "http://localhost:4566"
    lambda         = "http://localhost:4566"
    s3             = "http://s3.localhost.localstack.cloud:4566"
    sns            = "http://localhost:4566"
    sqs            = "http://localhost:4566"
    sts            = "http://localhost:4566"
    ecs            = "http://localhost:4566"
    elbv2          = "http://localhost:4566" 
  }
}

resource "aws_s3_bucket" "book_bucket" {
  bucket = "book-bucket-4f6f1f88-f5a5-4e82-a1ee-3b9cb4c105e5"
}
