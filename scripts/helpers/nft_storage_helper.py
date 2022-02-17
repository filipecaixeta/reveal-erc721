import requests
import subprocess
import random
import os

url = "https://api.nft.storage"
headers = {
  'Authorization': 'Bearer '+os.environ.get("NFT_STORAGE_TOKEN")
}
session = requests.session()


# _to_car packs a folder into a .car file
def _to_car(folder: str, wrapWithDirectory: bool = False) -> str:
    temp_car = str(int(random.random()*(2**32)))+".car"
    wwd = f"--wrapWithDirectory {'true' if wrapWithDirectory else 'false'}"
    stdout = subprocess.Popen(
        f"npx ipfs-car {wwd} --pack {folder} --output {temp_car}",
        shell=True, stdout=subprocess.PIPE
    ).stdout.read().decode().split("\n")
    lines = [line.strip() for line in stdout if line.strip()]
    car = lines[0].split(": ")[1]+".car"
    os.rename(temp_car, car)
    return car


# _upload_car uploads a car file to nft.storage
def _upload_car(car: str) -> str:
    with open(car, 'rb') as payload:
        response = session.request("POST", url+"/upload", headers={
            **headers, 'Content-Type': 'application/car'
        }, data=payload)
    if response.status_code == 200:
        return response.json()["value"]["cid"]
    else:
        return ""


# upload_to_ipfs uploads a folder or file to nft.storage
def upload_to_ipfs(folder: str, wrapWithDirectory: bool) -> str:
    car = _to_car(folder, wrapWithDirectory)
    url = _upload_car(car)
    os.remove(car)
    return url
