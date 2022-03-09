from multiprocessing import connection
import praw
import re
from pprint import pprint
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

connection = os.environ['DB_CONNECTION']
cluster = pymongo.MongoClient(
    f"{connection}?retryWrites=true&w=majority")
db = cluster['manga-scraper']


def scrape():
    urls = db['scans'].find_one({})
    if not urls:
        urls = set()
    reddit = praw.Reddit(
        client_id="wEBZeE2Bh10Ki1kCrchhKQ",
        client_secret="XBQQVa1bfXj1I2vqzAgncn4B3yjUUg",
        user_agent="manga scraper by u/27bslash",
    )
    for i, submission in enumerate(reddit.subreddit("manga").new(limit=50)):
        if '[DISC]' in submission.title and 'reddit' not in submission.url:
            domain = extract_domain(submission.url)
            # urls.append(submission.url)
            # pprint(vars(submission))
            urls.add(domain)
    db['scans'].find_one_and_update({}, {'$set': {'urls': list(urls)}}, upsert=True)


def extract_domain(url):
    regex = r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/?\n]+)"
    return re.search(regex, url).group()


def main():
    scrape()


if __name__ == '__main__':
    main()
