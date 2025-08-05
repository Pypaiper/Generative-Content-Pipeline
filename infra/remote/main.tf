



provider "aws" {
  region = var.region # Example for AWS, replace with your desired region
}

terraform {
  backend "s3" {
    bucket = "terraform-state-bucket-keeper"
    key    = "state.tfstate"
    region =  "us-west-2"
  }
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

  description = "Allow traffic to RDS from SageMaker"
  name        = "rds-security-group"

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
  engine_version       = "8.0"
  instance_class       = "db.t3.micro"
  db_name              = var.db_name
  username             = var.db_user
  password             = var.db_password # Use secrets management in production
  parameter_group_name = "default.mysql8.0"
  skip_final_snapshot  = true
  publicly_accessible  = false # Adjust based on security requirements
  multi_az             = false # Crucial for free-tier eligibility
}


resource "aws_iam_role" "sagemaker_role" {
  name        = "sagemaker-notebook-role"


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

  description = "Allows SageMaker to access S3 for data and model artifacts."
  name        = "sagemaker-s3-access-policy"


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
  name        = "my-lifecycle-config"

  on_start ="CiMhL2Jpbi9iYXNoCgpzZXQgLWV4CgpZT1VSX0VOVl9WQVJJQUJMRV9OQU1FPURCX05BTUUKCk5PVEVCT09LX0FSTj0kKGpxICcuUmVzb3VyY2VBcm4nIC9vcHQvbWwvbWV0YWRhdGEvcmVzb3VyY2UtbWV0YWRhdGEuanNvbiAtLXJhdy1vdXRwdXQpClRBRz0kKGF3cyBzYWdlbWFrZXIgbGlzdC10YWdzIC0tcmVzb3VyY2UtYXJuICROT1RFQk9PS19BUk4gIHwganEgLXIgLS1hcmcgWU9VUl9FTlZfVkFSSUFCTEVfTkFNRSAiJFlPVVJfRU5WX1ZBUklBQkxFX05BTUUiIC4nVGFnc1tdIHwgc2VsZWN0KC5LZXkgPT0gJFlPVVJfRU5WX1ZBUklBQkxFX05BTUUpLlZhbHVlJyAtLXJhdy1vdXRwdXQpCnRvdWNoIC9ldGMvcHJvZmlsZS5kL2p1cHl0ZXItZW52LnNoCmVjaG8gImV4cG9ydCAkWU9VUl9FTlZfVkFSSUFCTEVfTkFNRT0kVEFHIiA+PiAvZXRjL3Byb2ZpbGUuZC9qdXB5dGVyLWVudi5zaAoKWU9VUl9FTlZfVkFSSUFCTEVfTkFNRT1EQl9VU0VSCgpOT1RFQk9PS19BUk49JChqcSAnLlJlc291cmNlQXJuJyAvb3B0L21sL21ldGFkYXRhL3Jlc291cmNlLW1ldGFkYXRhLmpzb24gLS1yYXctb3V0cHV0KQpUQUc9JChhd3Mgc2FnZW1ha2VyIGxpc3QtdGFncyAtLXJlc291cmNlLWFybiAkTk9URUJPT0tfQVJOICB8IGpxIC1yIC0tYXJnIFlPVVJfRU5WX1ZBUklBQkxFX05BTUUgIiRZT1VSX0VOVl9WQVJJQUJMRV9OQU1FIiAuJ1RhZ3NbXSB8IHNlbGVjdCguS2V5ID09ICRZT1VSX0VOVl9WQVJJQUJMRV9OQU1FKS5WYWx1ZScgLS1yYXctb3V0cHV0KQp0b3VjaCAvZXRjL3Byb2ZpbGUuZC9qdXB5dGVyLWVudi5zaAplY2hvICJleHBvcnQgJFlPVVJfRU5WX1ZBUklBQkxFX05BTUU9JFRBRyIgPj4gL2V0Yy9wcm9maWxlLmQvanVweXRlci1lbnYuc2gKCllPVVJfRU5WX1ZBUklBQkxFX05BTUU9REJfUEFTU1dPUkQKCk5PVEVCT09LX0FSTj0kKGpxICcuUmVzb3VyY2VBcm4nIC9vcHQvbWwvbWV0YWRhdGEvcmVzb3VyY2UtbWV0YWRhdGEuanNvbiAtLXJhdy1vdXRwdXQpClRBRz0kKGF3cyBzYWdlbWFrZXIgbGlzdC10YWdzIC0tcmVzb3VyY2UtYXJuICROT1RFQk9PS19BUk4gIHwganEgLXIgLS1hcmcgWU9VUl9FTlZfVkFSSUFCTEVfTkFNRSAiJFlPVVJfRU5WX1ZBUklBQkxFX05BTUUiIC4nVGFnc1tdIHwgc2VsZWN0KC5LZXkgPT0gJFlPVVJfRU5WX1ZBUklBQkxFX05BTUUpLlZhbHVlJyAtLXJhdy1vdXRwdXQpCnRvdWNoIC9ldGMvcHJvZmlsZS5kL2p1cHl0ZXItZW52LnNoCmVjaG8gImV4cG9ydCAkWU9VUl9FTlZfVkFSSUFCTEVfTkFNRT0kVEFHIiA+PiAvZXRjL3Byb2ZpbGUuZC9qdXB5dGVyLWVudi5zaAoKWU9VUl9FTlZfVkFSSUFCTEVfTkFNRT1EQl9QT1JUCgoKTk9URUJPT0tfQVJOPSQoanEgJy5SZXNvdXJjZUFybicgL29wdC9tbC9tZXRhZGF0YS9yZXNvdXJjZS1tZXRhZGF0YS5qc29uIC0tcmF3LW91dHB1dCkKVEFHPSQoYXdzIHNhZ2VtYWtlciBsaXN0LXRhZ3MgLS1yZXNvdXJjZS1hcm4gJE5PVEVCT09LX0FSTiAgfCBqcSAtciAtLWFyZyBZT1VSX0VOVl9WQVJJQUJMRV9OQU1FICIkWU9VUl9FTlZfVkFSSUFCTEVfTkFNRSIgLidUYWdzW10gfCBzZWxlY3QoLktleSA9PSAkWU9VUl9FTlZfVkFSSUFCTEVfTkFNRSkuVmFsdWUnIC0tcmF3LW91dHB1dCkKdG91Y2ggL2V0Yy9wcm9maWxlLmQvanVweXRlci1lbnYuc2gKZWNobyAiZXhwb3J0ICRZT1VSX0VOVl9WQVJJQUJMRV9OQU1FPSRUQUciID4+IC9ldGMvcHJvZmlsZS5kL2p1cHl0ZXItZW52LnNoCgoKIyByZXN0YXJ0IGNvbW1hbmQgaXMgZGVwZW5kZW50IG9uIGN1cnJlbnQgcnVubmluZyBBbWF6b24gTGludXggYW5kIEp1cHl0ZXJMYWIKQ1VSUl9WRVJTSU9OPSQoY2F0IC9ldGMvb3MtcmVsZWFzZSkKaWYgW1sgJENVUlJfVkVSU0lPTiA9PSAqJCJodHRwOi8vYXdzLmFtYXpvbi5jb20vYW1hem9uLWxpbnV4LWFtaS8iKiBdXTsgdGhlbgogICAgc3VkbyBpbml0Y3RsIHJlc3RhcnQganVweXRlci1zZXJ2ZXIgLS1uby13YWl0CmVsc2UKICAgIHN1ZG8gc3lzdGVtY3RsIC0tbm8tYmxvY2sgcmVzdGFydCBqdXB5dGVyLXNlcnZlci5zZXJ2aWNlCmZpCg=="

}


# SageMaker Notebook Instance
resource "aws_sagemaker_notebook_instance" "sagemaker_notebook" {

  name        = "my-sagemaker-notebook"
  instance_type        = "ml.t2.medium"
  role_arn             = aws_iam_role.sagemaker_role.arn
  subnet_id            = aws_subnet.sagemaker_private_subnet.id
  security_groups      = [aws_security_group.sagemaker_sg.id]
  direct_internet_access = "Enabled" # Set to Disabled for private subnets
  lifecycle_config_name = aws_sagemaker_notebook_instance_lifecycle_configuration.example.name
  tags = {
    Name = "my-sagemaker-notebook"
    DB_PORT = var.db_port
    DB_NAME = var.db_name
    DB_USER = var.db_user
    DB_PASSWORD = var.db_password
    BUCKET_NAME = var.bucket_name
  }
}


output "rds_endpoint" {
  value = aws_db_instance.rds_instance.address
  description = "The address of the RDS database instance."
}

output "sagemaker_notebook_url" {
  value = "${aws_sagemaker_notebook_instance.sagemaker_notebook.name}.notebook.${var.region}.sagemaker.aws"
  description = "The URL of the SageMaker notebook instance."
  sensitive = true
}



