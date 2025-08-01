
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



variable "db_name" {
    description = "The name of database."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}


variable "bucket_name" {
    description = "The name of s3 bucket."
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

data "aws_availability_zones" "azs" { state = "available" }



# Define private subnets for RDS
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone =  data.aws_availability_zones.azs.names[count.index]
}

# Define a public subnet for the SageMaker notebook (if internet access is needed)
resource "aws_subnet" "sagemaker_private_subnet" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone =  data.aws_availability_zones.azs.names[0]
}



resource "aws_s3_bucket" "my_bucket" {
  bucket = var.bucket_name

  lifecycle {
    prevent_destroy = true
  }
}



# Security group for the SageMaker notebook instance
resource "aws_security_group" "sagemaker_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "sagemaker-security-group"
  description = "Allow traffic from SageMaker to RDS"

  ingress {
    from_port   = 8192 # Example range, adjust based on your needs
    to_port     = 65535
    protocol    = "tcp"
    self        = true # Allow traffic within the same security group
    description = "Allow traffic between SageMaker applications"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # Allow outbound internet access if needed (consider a NAT Gateway for private subnets)
    description = "Allow all outbound traffic (with NAT if in private subnet)"
  }
  tags = {
    Name = "sagemaker-sg"
  }
}

# Security group for the RDS instance
resource "aws_security_group" "rds_sg" {
  vpc_id      = aws_vpc.main.id
  name        = "rds-security-group"
  description = "Allow traffic to RDS from SageMaker"

  ingress {
    from_port   = 3306 # Your RDS database port (e.g., PostgreSQL)
    to_port     = 3306
    protocol    = "tcp"
    security_groups = [aws_security_group.sagemaker_sg.id] # Allow traffic from SageMaker security group
    description = "Allow traffic from SageMaker notebook"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }
  tags = {
    Name = "rds-sg"
  }
}

# DB Subnet Group for RDS
resource "aws_db_subnet_group" "rds_subnet_group" {
  name        = "rds-subnet-group"
  subnet_ids  = aws_subnet.private[*].id
  description = "Subnet group for RDS instance"
  tags = {
    Name = "rds-subnet-group"
  }
}




# RDS instance
resource "aws_db_instance" "rds_instance" {

  db_subnet_group_name  = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  allocated_storage    = 20
  engine               = "mysql"
  engine_version       = "8.0.35"
  instance_class       = "db.t3.micro"
  db_name              = var.db_name
  username             = var.db_username
  password             = var.db_password # Use secrets management in production
  parameter_group_name = "default.mysql8.0"
  skip_final_snapshot  = true
  publicly_accessible  = false # Adjust based on security requirements
  multi_az             = false # Crucial for free-tier eligibility
}


resource "aws_iam_role" "sagemaker_role" {
  name = "sagemaker-notebook-role"

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
      {
        Action = "sts:AssumeRole"
        Effect   = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      },
    ]
  })
}

# Define the IAM policy for S3 access
resource "aws_iam_policy" "sagemaker_s3_policy" {
  name        = "sagemaker-s3-access-policy"
  description = "Allows SageMaker to access S3 for data and model artifacts."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
        ]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.my_bucket.arn,
          "${aws_s3_bucket.my_bucket.arn}/*",
        ]
      },
    ]
  })
}



resource "aws_iam_role_policy_attachment" "sagemaker_policy_attachment" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

resource "aws_iam_role_policy_attachment" "sagemaker_s3_attachment" {
  role       = aws_iam_role.sagemaker_role.name
  policy_arn = aws_iam_policy.sagemaker_s3_policy.arn
}



resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "example" {
  name = "my-lifecycle-config"

  on_start = <<-EOF
#!/bin/bash
export DB_NAME="${var.db_name}"
export DB_USERNAME="${var.db_username}"
export DB_PASSWORD="${var.db_password}"
export DB_HOST="${aws_db_instance.rds_instance.address}"
# You can also set variables here that are sourced by your notebook
EOF
}


# SageMaker Notebook Instance
resource "aws_sagemaker_notebook_instance" "sagemaker_notebook" {
  name                 = "my-sagemaker-notebook"
  instance_type        = "ml.t2.medium"
  role_arn             = aws_iam_role.sagemaker_role.arn
  subnet_id            = aws_subnet.sagemaker_private_subnet.id
  security_groups      = [aws_security_group.sagemaker_sg.id]
  direct_internet_access = "Enabled" # Set to Disabled for private subnets
  lifecycle_config_name = aws_sagemaker_notebook_instance_lifecycle_configuration.example.name
  tags = {
    Name = "my-sagemaker-notebook"
  }
}


output "rds_endpoint" {
  value = aws_db_instance.rds_instance.address
  description = "The address of the RDS database instance."
}

output "sagemaker_notebook_url" {
  value = "${aws_sagemaker_notebook_instance.sagemaker_notebook.name}.notebook.${var.region}.sagemaker.aws"
  description = "The URL of the SageMaker notebook instance."
  sensitive=true
}



