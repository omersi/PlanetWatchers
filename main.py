import json
import os
import random
from urllib import request

import boto3
import progressbar
import requests

pbar = None


def list_resources() -> dict:
    """List images that intersect with a given geometry.

    Raises:
        ValueError: Error getting data from scihub.copernicus.eu

    Returns:
        dict: scihub.copernicus.eu json object
    """
    geometry = os.getenv("GEOM")
    url = f'https://scihub.copernicus.eu/dhus/search?q=footprint:\"Intersects({geometry})\"&format=json&filter=hour(IngestionDate) lt 24'  # noqa

    print(f"Searching for images of {url}")

    response = requests.request(
        "GET", url, auth=(os.getenv("DHUS_USER"),
                          os.getenv("DHUS_PASSWORD")))  # type: ignore

    print("Got response from server")

    if response.status_code == 200:

        _resources = json.loads(response.text)

        if "error" in _resources["feed"].keys():
            raise KeyError(response.text)
        return _resources

    raise ValueError("Error getting data from %s", url)


def show_progress(block_num, block_size, total_size):
    """ProgressBar function for downloading objects

    """
    global pbar
    if pbar is None:
        pbar = progressbar.ProgressBar(maxval=total_size)
        pbar.start()

    downloaded = block_num * block_size
    if downloaded < total_size:
        pbar.update(downloaded)
    else:
        pbar.finish()
        pbar = None


def download_resource(resources: dict, counter: int) -> str:
    """Download a single resource from a dictionary of resources.

    Args:
        resources (dict): Resources dict generated in list_resources
        counter (int): counter that checks if the an image was downloaded. can be either 0 or 1.

    Raises:
        Exception: Could not download resource

    Returns:
        str: resource id (for example, f05fdf89-12e4-4423-85df-00bff99ffd90)
    """

    entries = [x for x in resources["feed"]["entry"]]

    if len(entries) > 0:
        randomlist = random.sample(range(0, len(entries) - 1), 5)

        num = randomlist[2]
        resource_id = entries[num]["id"]
        url = f"https://scihub.copernicus.eu/dhus/odata/v1/Products('{resource_id}')/$value"

        opener = request.build_opener()
        opener.addheaders = [('Authorization',
                              f'Basic {os.getenv("ENCODED_CREDS")}')]
        request.install_opener(opener)

        print(f"Downloading {resource_id}")
        response = request.urlretrieve(url, f"/tmp/{resource_id}.zip",
                                       show_progress)

        print(f"Finished Downloading {response[0]}")
        return resource_id
    else:
        print("Resoureces list is empty. retrying")
        if counter == 0:
            lambda_handler(1, None)
    raise Exception("Could not download resource")


def upload_to_s3(resource_id: str) -> None:
    """Uploads the resource to S3 bucket

    Args:
        resource_id (str): resource id (for example, f05fdf89-12e4-4423-85df-00bff99ffd90)
    """
    bucket = os.getenv("AWS_BUCKET")
    s3_res = boto3.resource("s3")
    print(f"Uploading {resource_id}.zip to s3://{bucket}/")
    s3_res.meta.client.upload_file(f"/tmp/{resource_id}.zip", f"{bucket}",
                                   f"{resource_id}.zip")


def lambda_handler(event, context):
    """Lambda handler 

    """
    resources = list_resources()
    counter = 0
    if event == 0:
        counter = 1
    resource_id = download_resource(resources, counter)
    upload_to_s3(resource_id)


if __name__ == "__main__":
    lambda_handler("e", "c")
