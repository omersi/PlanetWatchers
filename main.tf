data "aws_caller_identity" "current" {}


module "lambda_function" {
  source = "terraform-aws-modules/lambda/aws"

  function_name          = var.tag_name
  description            = "Download file from scihub.copernicus.eu and upload it to S3"
  handler                = "main.lambda_handler"
  runtime                = "python3.8"
  timeout                = 600
  memory_size            = 2048
  ephemeral_storage_size = 5000
  publish                = true

  store_on_s3 = true
  s3_bucket   = var.aws_lambda_code_bucket
  s3_prefix   = "planetwathcers-lambda-builds/"

  source_path = [{
    path             = "../pw_python"
    pip_requirements = "../pw_python/requirements.txt"
  }]

  tags = {
    Name = var.tag_name
  }

  environment_variables = {
    DHUS_USER     = var.dhus_user
    DHUS_PASSWORD = var.dhus_password
    GEOM          = var.geom
    WORKDIR       = var.workdir
    ENCODED_CREDS = var.encoded_credentials
    AWS_BUCKET    = var.aws_bucket
  }

  allowed_triggers = {
    OneRule = {
      principal  = "events.amazonaws.com"
      source_arn = aws_cloudwatch_event_rule.planetwatchers_alaska.arn
    }
  }

}

resource "aws_cloudwatch_event_rule" "planetwatchers_alaska" {
  name                = "TriggerPlanetWatchersLambda"
  description         = "Triggers PlanetWatchers Lambda daily at 02:34"
  schedule_expression = "cron(34 02 * * ? *)"
  tags = {
    Name = var.tag_name
  }

}

resource "aws_cloudwatch_event_target" "planetwatchers_scheduler" {
  rule = aws_cloudwatch_event_rule.planetwatchers_alaska.name
  arn  = module.lambda_function.lambda_function_arn
}

