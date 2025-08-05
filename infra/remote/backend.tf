variable "region" {
    description = "The region of deployment."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}

variable "db_user" {
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

variable "db_port" {
    description = "The name of database."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}

variable "bucket_name" {
    description = "The name of s3 bucket."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}

