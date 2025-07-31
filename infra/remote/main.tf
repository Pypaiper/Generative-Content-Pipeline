
variable "region" {

    description = "The region of deployment."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}

variable "db_username" {
    description = "The admin username of database."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}

variable "db_password" {
    description = "The admin password of database."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}


provider "aws" {
  region = var.region # Example for AWS, replace with your desired region
}



# Define your VPC
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  # ... other VPC settings
}


# Define private subnets for RDS
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
}


# Define a public subnet for the SageMaker notebook (if internet access is needed)
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.0.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
}


# Create a DB Subnet Group for RDS
resource "aws_db_subnet_group" "default" {
  subnet_ids = aws_subnet.private[*].id
  description = "DB subnet group"
}


# Security group for the SageMaker notebook
resource "aws_security_group" "sagemaker_sg" {
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 8888 # Or the port your notebook uses
    to_port     = 8888
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Restrict as needed
  }
  egress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    cidr_blocks = [
      aws_subnet.private[0].cidr_block, # Allow traffic to RDS subnets
      aws_subnet.private[1].cidr_block,
      # ... other necessary egress rules
    ]
  }
}


# Security group for the RDS database
resource "aws_security_group" "rds_sg" {
  vpc_id = aws_vpc.main.id
  ingress {
    from_port = 5432 # Or your RDS database port
    to_port   = 5432
    protocol  = "tcp"
    security_groups = [
      aws_security_group.sagemaker_sg.id, # Allow access from the SageMaker notebook's security group
    ]
  }
}



# SageMaker IAM role with necessary permissions
resource "aws_iam_role" "sagemaker_role" {
  name = "sagemaker_rds_access_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      },
    ]
  })
}

# Attach policies to the SageMaker role allowing access to RDS, S3, etc.
resource "aws_iam_policy_attachment" "sagemaker_rds_policy_attachment" {
  name       = "sagemaker_rds_access"
  roles      = [aws_iam_role.sagemaker_role.name]
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess" # Adjust for least privilege
}


# Launch the SageMaker notebook instance
resource "aws_sagemaker_notebook_instance" "rds_notebook" {
  name             = "my-rds-notebook"
  instance_type    = "ml.t2.medium"
  role_arn         = aws_iam_role.sagemaker_role.arn
  subnet_id        = aws_subnet.public.id # Or a private subnet with NAT Gateway
  security_groups  = [aws_security_group.sagemaker_sg.id]
  direct_internet_access = "Enabled" # Or "Disabled" if using a NAT Gateway
}



data "aws_s3_bucket" "book" {
  bucket = "book-terraform-s3-bucket-name"
}

output "my_bucket_name" {
  value = "${data.aws_s3_bucket.book.bucket}"
}


resource "aws_db_instance" "mysql" {
  allocated_storage    = 20
  storage_type         = "gp2"
  engine               = "mysql"
  engine_version       = "8.0.41" # Or a version supported by free tier
  instance_class       = "db.t4g.micro" # Or db.t3.micro for free tier
  name                 = "book"
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = "default.mysql8.0"
  skip_final_snapshot  = true
  publicly_accessible  = true # For easy access in development/testing
  # Ensure this aligns with your free tier limits
  multi_az             = false

  db_subnet_group_name = aws_db_subnet_group.default.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
}
