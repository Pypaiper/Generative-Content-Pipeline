
variable "region" {

    description = "The region of deployment."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}

variable "bucket_name" {

    description = "The region of deployment."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}



provider "aws" {
  region = var.region # Example for AWS, replace with your desired region
}

resource "aws_s3_bucket" var.bucket_name {
  bucket = "my-unique-terraform-s3-bucket-name" # Choose a globally unique bucket name
  acl    = "private" # Or "public-read", "public-read-write", etc., depending on your needs
  tags = {
    Environment = "Deployment"
    Project     = "Generative-Content-Pipeline"
  }
}
