import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv()

lambda_client = boto3.client("lambda")
AWS_ID = os.getenv("AWS_ID")

# Put this in a file called {function_name}.py and then zip to {function_name}.zip
def lambda_handler(event, context):
    message = "Hello {} {}!".format(event["first_name"], event["last_name"])
    return {"message": message}


function_name = "HelloWorld"
function_role = f"arn:aws:iam::{AWS_ID}:role/lambda_basic_execution"

lambda_client.create_function(
    FunctionName=function_name,
    Runtime="python3.7",
    Role=function_role,
    Handler=f"{function_name}.lambda_handler",
    Code={"ZipFile": open(f"{function_name}.zip", "rb").read()},
)


def lambda_funcs():
    client = boto3.client("lambda")
    response = client.list_functions()
    lambda_name = response["Functions"][0]["FunctionName"]
    event = {"first_name": "Vegard", "last_name": "Stikbakke"}
    event_json = json.dumps(event)
    resp = client.invoke(FunctionName=lambda_name, Payload=event_json)
    function_response = resp["Payload"].read()
    print(function_response)
