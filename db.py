import time
from dotenv import load_dotenv
import os
import pymongo
import requests

load_dotenv()


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
    connection = os.environ["DB_CONNECTION"]
    cluster = pymongo.MongoClient(f"{connection}?retryWrites=true&w=majority")
    db = cluster["manga-scraper"]
