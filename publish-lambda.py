import boto3

from aws_id import aws_id

lambda_client = boto3.client("lambda")

fn_name = "HelloWorld"
fn_role = f"arn:aws:iam::{aws_id}:role/lambda_basic_execution"

lambda_client.create_function(
    FunctionName=fn_name,
    Runtime="python3.7",
    Role=fn_role,
    Handler="{0}.lambda_handler".format(fn_name),
    Code={"ZipFile": open("{0}.zip".format(fn_name), "rb").read()},
)
