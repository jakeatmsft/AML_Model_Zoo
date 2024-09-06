import argparse
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from azure.ai.ml import MLClient
from azure.ai.ml.constants import AssetTypes
from azure.ai.ml.entities import (
    BuildContext,
    Environment,
    ManagedOnlineDeployment,
    ManagedOnlineEndpoint,
    Model,
    ModelPackage
)
from azure.ai.ml.identity import AzureMLOnBehalfOfCredential
from azure.storage.blob import BlobServiceClient, BlobClient

from utils.common_utils import get_mlclient

def parse_url(url):
    parsed_url = urlparse(url)

    account = parsed_url.netloc.split('.')[0]
    container = parsed_url.path.lstrip('/').split('/')[0]
    path = '/'.join(parsed_url.path.lstrip('/').split('/')[1:])

    return account, container, path

parser = argparse.ArgumentParser("update_env")
parser.add_argument("--model_package", type=str, help="model_name")
parser.add_argument("--model_output", type=str, default="default_model_path", help="Path of output model")

args = parser.parse_args()

print("env update model started...")

lines = [
    f"model_package: {args.model_package}",
    f"Model output path: {args.model_output}",
]

for line in lines:
    print(line)

model_package_folder = args.model_package

print("Getting ML client...")
ml_client = get_mlclient()
print("ML client: ", ml_client)

model_package_info = None
#open file named model.txt and read to variable in the model_package folder 
with open(f"{model_package_folder}/model.txt", "r") as f:
    model_package_info = f.read().strip()

print(model_package_info)

# read model_package_info of format :{"model_package_name": model_package_name, "model_name": model.name, "model_version": model.version} into json object

model_info = json.loads(model_package_info)
print("Model Package Info:")
print("Model Package Name:", model_info["model_package_name"])
print("Model Name:", model_info["model_name"])
print("Model Version:", model_info["model_version"])


foldername = 'build_context'

if not os.path.exists(foldername):
    os.mkdir(foldername)

#Retrieve the build context of the model package
model_env = ml_client.environments.get(model_info["model_package_name"], '1')
url = model_env.build.path
account, container, path = parse_url(url)

# Create a blob service client
credential = ml_client._credential
blob_service_client = BlobServiceClient(account_url=f"https://{account}.blob.core.windows.net", credential=credential)

# Get a blob client for the blob we want to download
blob_client = blob_service_client.get_blob_client(container, f"{path}/Dockerfile")

# Download the blob to a local file
with open(f"{foldername}/dockerfile", "wb") as download_file:
    download_file.write(blob_client.download_blob().readall())

#Get conda file from model
model_path = ml_client.models.get(model_info['model_name'],  model_info["model_version"]).path

# assuming model_path is a string that contains 'paths'
match = re.search(r'paths(.*)', model_path)
result = match.group(1)
mpath = result[1:]
mblob_client = blob_service_client.get_blob_client(container, f"{mpath}/conda.yaml")

# Download the conda file to a local file
with open(f"{foldername}/conda.yaml", "wb") as download_file:
    download_file.write(mblob_client.download_blob().readall())

# read local dockerfile
with open(f"{foldername}/dockerfile", "r") as file:
    dockerfile_lines = file.readlines()

# find lines with wget command and get only the first part of the RUN command
wget_lines = [(i, line.split('// && wget', 1)[0]) for i, line in enumerate(dockerfile_lines, start=1) if 'wget' in line]

if(wget_lines) :
    print(wget_lines[0])
    replacement_linenum = wget_lines[0][0]-1
    replacement_text = wget_lines[0][1]

    dockerfile_lines[replacement_linenum] = f"{replacement_text}\n"
    # Add new line after replacement_linenum
    new_line = "COPY conda.yaml ${AZUREML_MODEL_DIR}/${MLFLOW_MODEL_FOLDER}\n"
    dockerfile_lines.insert(replacement_linenum + 1, new_line)

    print(dockerfile_lines)
    #write the new dockerfile
    with open(f"{foldername}/dockerfile", "w") as file:
        file.writelines(dockerfile_lines)

url = model_env.build.path
account, container, path = parse_url(url)

# Create a blob service client
blob_service_client = BlobServiceClient(account_url=f"https://{account}.blob.core.windows.net", credential=credential)

#save the new dockerfile to path
blob_client = blob_service_client.get_blob_client(container, f"{path}/Dockerfile")
with open(f"{foldername}/dockerfile", "rb") as data:
    blob_client.upload_blob(data, overwrite=True)
print('uploaded dockerfile')

#save the conda.yaml to path
blob_client = blob_service_client.get_blob_client(container, f"{path}/conda.yaml")
with open(f"{foldername}/conda.yaml", "rb") as data:
    blob_client.upload_blob(data, overwrite=True)

print('uploaded conda file')

print("Model environment updated successfully")
context_path = f"https://{account}.blob.core.windows.net/{container}/{path}"
print(context_path)

model_env.version= str(int(time.time()))
model_env.build = BuildContext(path=context_path,
                               dockerfile_path='Dockerfile')

ml_client.environments.create_or_update(model_env)
