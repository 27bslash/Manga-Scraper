import time
from dotenv import load_dotenv
import os
import pymongo
import requests

base_dir = os.path.dirname(os.path.abspath(__file__))

# Path to the .env file
env_path = os.path.join(base_dir, '.env')
print(env_path)
load_dotenv(env_path)


def net_test(retries=500):
    for i in range(retries):
        try:
            req = requests.get("https://www.google.co.uk/")
            print("connected to the internet")
            return True
        except Exception as e:
            time.sleep(1)
    return False


if net_test():
    time.sleep(60)
    connection = os.environ["DB_CONNECTION"]
    cluster = pymongo.MongoClient(f"{connection}?retryWrites=true&w=majority")
    db = cluster["manga-scraper"]
