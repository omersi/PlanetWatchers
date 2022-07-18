import json
import pathlib
import random
from urllib import request

import boto3
import progressbar
import requests

pbar = None


def list_images() -> dict:

    url = "https://scihub.copernicus.eu/dhus/search?q=footprint:\"Intersects(POLYGON((-150.34828760694975 61.19425431146611,-150.11048603553027 61.183240545179586,-150.14198702291313 61.10394711470604,-150.35075827262685 61.1152869427646,-150.35075827262685 61.1152869427646,-150.34828760694975 61.19425431146611)))\"&format=json&filter=hour(IngestionDate) lt 24"

    print(f"Searching for images of {url}")

    response = requests.request("GET",
                                url,
                                auth=("omerls", "[PASSWORD_HERE]"))

    print("Got response from server")

    if response.status_code == 200:
        return json.loads(response.text)

    raise ValueError("Error getting data from %s", url)


def show_progress(block_num, block_size, total_size):
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


def download_resource(resources: dict) -> str:
    entries = [x for x in resources["feed"]["entry"]]

    if len(entries) > 0:
        randomlist = random.sample(range(0, len(entries) - 1), 5)

        for num in randomlist:
            id = entries[num]["id"]
            url = f"https://scihub.copernicus.eu/dhus/odata/v1/Products('{id}')/$value"

            opener = request.build_opener()
            opener.addheaders = [
                ('Authorization', 'Basic [TOKEN_HERE]')
            ]
            request.install_opener(opener)

            print(f"Downloading {id}")
            response = request.urlretrieve(url, f"/tmp/{id}.zip",
                                           show_progress)

            print(f"Finished Downloading {response[0]}")
            return id


def upload_to_s3(resource_id: str) -> None:

    s3_res = boto3.resource("s3")
    print(f"Uploading {resource_id}.zip to s3://[S3_BUCKET]/")
    s3_res.meta.client.upload_file(f"/tmp/{resource_id}.zip", "[BUCKET_HERE]",
                                   f"{resource_id}.zip")


def lambda_handler(event, context):
    resources = list_images()
    resource_id = download_resource(resources)
    upload_to_s3(resource_id)


if __name__ == "__main__":
    lambda_handler("e", "c")
