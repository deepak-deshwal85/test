terraform {
  backend "s3" {
    bucket         = "relaydesk-terraform-state-bucket"
    key            = "relaydesk/prod/terraform.tfstate"
    region         = "ap-south-1"
    encrypt        = true
    use_lockfile   = true
  }
}
