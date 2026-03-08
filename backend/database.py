import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

from pathlib import Path

# Load from the parent directory of 'neural-detectives'
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

MONGODB_URI = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "neuralDetectives"

import certifi

client = None

def get_database():
    global client
    if client is None:
        client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where())
    return client[DB_NAME]

async def close_database_connection():
    global client
    if client:
        client.close()
        client = None
