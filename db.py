from dotenv import load_dotenv
import os
import pymongo
load_dotenv()
connection = os.environ['DB_CONNECTION']
cluster = pymongo.MongoClient(
    f"{connection}?retryWrites=true&w=majority")
db = cluster['manga-scraper']