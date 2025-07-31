
variable "region" {

    description = "The region of deployment."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}

provider "aws" {
  region = var.region # Example for AWS, replace with your desired region
}


# resource "aws_instance" "example_instance" {
#   ami           = "ami-054b7fc3c333ac6d2" # Replace with a valid AMI ID for your region
#   instance_type = "t2.micro"
# }
