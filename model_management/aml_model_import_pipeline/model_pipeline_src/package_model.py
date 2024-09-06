import argparse
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import os
import json
import time
from utils.common_utils import get_mlclient
from azure.ai.ml import MLClient
from azure.ai.ml.identity import AzureMLOnBehalfOfCredential
from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    ManagedOnlineEndpoint,
    ManagedOnlineDeployment,
    Model,
    Environment,
    ModelPackage,
    CodeConfiguration,
    AzureMLOnlineInferencingServer
)
from azure.ai.ml.constants import AssetTypes
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import BlobClient
from urllib.parse import urlparse

parser = argparse.ArgumentParser("package_model")
parser.add_argument("--model_name", type=str, help="model_name")
parser.add_argument("--model_version", type=str, default="latest", help="model_version")

parser.add_argument("--model_output", type=str, default="default_model_path", help="Path of output model")

args = parser.parse_args()

print("Package model started...")

lines = [
    f"model_name: {args.model_name}",
    f"model_version: {args.model_version}",
    f"Model output path: {args.model_output}",
]

output_folder = args.model_output

for line in lines:
    print(line)

model_version = args.model_version
model_name = args.model_name

print("Getting ML client...")
ml_client = get_mlclient()
print("ML client: ", ml_client)

print("Listing available versions of the model...")
version_list = list(
    ml_client.models.list(model_name)
)
ml_model = None

if len(version_list) == 0:
    raise Exception(f"No model named {model_name} found in registry")
else:
    if model_version == "latest":
        model_version = version_list[0].version
    
    ml_model = ml_client.models.get(model_name, model_version)
    print(
        f"Using model name: {ml_model.name}, version: {ml_model.version}, id: {ml_model.id} "
    )

print("Creating model package...")

model = ml_model
model_package_name = f"pkg-{model.name}-{model.version}"
model_package_version = str(int(time.time()))

#check if model_package_name exists
try:
    # Attempt to get the model by name and version
    existing_env_package = ml_client.environment.get(name=model_package_name, version='1')
    print("Model package already exists in local registry.")
    print("Skipping package.")
    output_file = os.path.join(output_folder, f"model.txt")
    with open(output_file, "w") as file:
        file.write(json.dumps({"model_package_name": model_package_name, "model_name": model.name, "model_version": model.version}))    
    print(f"Model package written to: {output_file}")      
    exit(0)
except Exception as e:
    # If the model does not exist, an exception will be caught here
    print("Model does not exist or an error occurred while checking:", str(e))


package_config = ModelPackage(
    environment_name = model_package_name,
    target_environment=model_package_name,
    target_environment_version = model.version,
    inferencing_server=AzureMLOnlineInferencingServer(),
)

model_package = ml_client.models.package(model.name, model.version, package_config)

#write file with print(model_package) to output_folder
output_file = os.path.join(output_folder, f"model.txt")
with open(output_file, "w") as file:
    file.write(json.dumps({"model_package_name": model_package_name, "model_name": model.name, "model_version": model.version}))
print(f"Model package written to: {output_file}")
