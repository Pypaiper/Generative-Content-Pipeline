
variable "region" {

    description = "The region of deployment."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}



provider "aws" {
  region = var.region # Example for AWS, replace with your desired region
}


data "aws_s3_bucket" "book" {
  bucket = "book-terraform-s3-bucket-name"
}

output "my_bucket_name" {
  value = "${data.aws_s3_bucket.book.bucket}"
}


