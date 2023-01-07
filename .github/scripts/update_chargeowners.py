"""Update available charge owners from Energi Data Service API."""

import os

import requests

url = 'https://api.energidataservice.dk/dataset/DatahubPricelist?start=1970-01-01&filter={"Note":["Nettarif C time"]}'

payload = {}
headers = {"Content-Type": "application/json"}

response = requests.request("GET", url, headers=headers, data=payload)

data = response.json()
chargeowners = []

for entry in data["records"]:
    if (
        entry["ChargeOwner"] not in chargeowners
        and "UDGÅET" not in entry["ChargeOwner"]
    ):
        chargeowners.append(entry["ChargeOwner"])

cur_dir = os.path.dirname(os.path.realpath(__file__))
data_file = (
    cur_dir
    + "/../../custom_components/energidataservice/tariffs/energidataservice/chargeowners.py"
)

print(data_file)
f = open(data_file, "w", encoding="UTF-8")
f.write('"""Valid Charge Owners for Energi Data Service connector."""\r\n')
f.write("\r\n")
f.write("CHARGEOWNERS = [\r\n")

for chargeowner in chargeowners:
    f.write(f'    "{chargeowner}",\r\n')

f.write("]\r\n")
f.close()
