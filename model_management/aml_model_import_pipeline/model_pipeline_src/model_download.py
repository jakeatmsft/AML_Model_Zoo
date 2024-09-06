import argparse
from pathlib import Path
from uuid import uuid4
from datetime import datetime
import os
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

parser = argparse.ArgumentParser("catalog_download")
parser.add_argument("--registry", type=str, help="registry name")
parser.add_argument("--model_name", type=str, help="model_name")
parser.add_argument("--model_output", type=str, default="default_model_path", help="Path of output model")

args = parser.parse_args()

print("Download catalog model started...")

lines = [
    f"registry: {args.registry}",
    f"model_name: {args.model_name}",
    f"Model output path: {args.model_output}",
]

for line in lines:
    print(line)

print(os.environ["MLFLOW_RUN_ID"])

registry_name = args.registry
model_name = args.model_name

print("Getting ML client...")
ml_client = get_mlclient()
print("ML client: ", ml_client)

print("Getting registry client...")
reg_client = get_mlclient(registry_name=registry_name)
print("Registry client: ", reg_client)

print("Listing available versions of the model...")
version_list = list(
    reg_client.models.list(model_name)
)

ml_model = None
hf_tgi = True  # If text-generation-inference (hf container) is supported for model

if len(version_list) == 0:
    raise Exception(f"No model named {model_name} found in registry")
else:
    model_version = version_list[0].version
    ml_model = reg_client.models.get(model_name, model_version)
    if "inference_supported_envs" in ml_model.tags:
        if "hf_tgi" in ml_model.tags["inference_supported_envs"]:
            hf_tgi = True
    print(
        f"Using model name: {ml_model.name}, version: {ml_model.version}, id: {ml_model.id} "
    )

# Check if model already exists in local registry:

try:
    # Attempt to get the model by name and version
    existing_model = ml_client.models.get(name=ml_model.name, version=ml_model.version)
    print("Model already exists in local registry.")
    print("Skipping model download.")
    filename = 'out.txt'
    with open(f'{args.model_output}/{filename}', 'w') as f:
        f.write(str(existing_model))
        
    exit(0)
except Exception as e:
    # If the model does not exist, an exception will be caught here
    print("Model does not exist or an error occurred while checking:", str(e))

# Download model 
print("Downloading model...")
download_path='.'
reg_client.models.download(ml_model.name, ml_model.version, download_path)
print("Model downloaded.")

print("Creating or updating model...")
file_model = Model(
    path=f"{download_path}/{model_name}/mlflow_model_folder",
    type=AssetTypes.MLFLOW_MODEL,
    name=ml_model.name,
    version=ml_model.version,
    description="Model created from local file.",
)
ml_client.models.create_or_update(file_model)

# Assuming args.model_output is the path to the output file
filename = 'out.txt'
with open(f'{args.model_output}/{filename}', 'w') as f:
    f.write(str(file_model))