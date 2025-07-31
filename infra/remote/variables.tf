variable "region" {
    description = "The region of deployment."
    type        = string
    sensitive   = true # Mark as sensitive to prevent logging
}
