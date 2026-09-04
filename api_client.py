import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("NEXON_API_KEY")
BASE_URL = "https://open.api.nexon.com/maplestory/v1"
HEADERS = {"x-nxopen-api-key": API_KEY}

async def get_ocid(character_name):
    url = f"{BASE_URL}/id?character_name={character_name}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                return (await response.json()).get("ocid")
    return None

async def get_character_basic(ocid):
    url = f"{BASE_URL}/character/basic?ocid={ocid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                return await response.json()
    return None

async def get_character_stat(ocid):
    url = f"{BASE_URL}/character/stat?ocid={ocid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                return await response.json()
    return None

async def get_character_items(ocid):
    url = f"{BASE_URL}/character/item-equipment?ocid={ocid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as response:
            if response.status == 200:
                return await response.json()
    return None