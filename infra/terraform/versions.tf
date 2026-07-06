terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Uncomment after creating the S3 bucket and DynamoDB table (see backend.tf.example).
  # backend "s3" {}
}
