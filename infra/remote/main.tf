
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






