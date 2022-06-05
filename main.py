import datetime
import os
import re
import sys
import time
from pprint import pprint

import praw
import pymongo
import requests
from apscheduler.schedulers.background import BlockingScheduler
from dotenv import load_dotenv


load_dotenv()
connection = os.environ['DB_CONNECTION']
cluster = pymongo.MongoClient(
    f"{connection}?retryWrites=true&w=majority")
db = cluster['manga-scraper']


class Source:
    db = db

    def update_manga_dict(self, manga, item):
        if item['latest'] > manga['chapter']:
            manga['read'] = False
            # this will run every time make it update only once
            manga['latest'] = item['latest']
            if 'link' not in manga:
                manga['link'] = item['link']
            manga['sources'] = self.update_sources(manga,
                                                   item['scansite'], item)
            manga['domain'] = item['domain']
            manga['test'] = True
        else:
            manga['read'] = True
            manga['sources'] = self.update_sources(manga,
                                                   item['scansite'], item)
        return manga

    def update_sources(self, curr, scansite,  item):
        db_entry = db['all_manga'].find_one({'title': item['title']})
        # if 'sss' in item['title']:
        # print(scansite, db_entry['sources'])
        source_string = {
            'url': curr['link'], 'latest': item['latest'], 'latest_link': item['link'], 'time_updated': item['time_updated']}
        if not db_entry:
            db_entry = {'sources': {}}
        if 'sources' not in db_entry:
            db_entry['sources'] = {}
        if'any' not in db_entry['sources']:
            db_entry['sources']['any'] = source_string
        if db_entry['sources']['any']['latest'] < item['latest']:
            db_entry['sources']['any'] = source_string
        elif db_entry['sources']['any']['time_updated'] >= item['time_updated']:
            #     print('any')
            # print(item['title'])
            # print(db_entry['sources'])
            db_entry['sources']['any'] = source_string
        # print(db_entry['sources']['any']['time_updated'], item['time_updated'], db_entry['sources']
        #       ['any']['latest'], item['latest'], db_entry['sources']['any']['time_updated'] < item['time_updated'])
        db_entry['sources'][scansite] = source_string
        return db_entry['sources']

    def clean_title(self, title):
        return re.sub(
            r'\s\s+', ' ', title).strip().replace(' ', '-').replace('\n', '').lower()

    def clean_chapter(self, chapter):
        regex = r"(?<=Chapter )\d+"
        match = re.search(regex, chapter)
        if match:
            return match.group().strip()
        else:
            return chapter.replace('Chapter ', '').strip()

    def convert_time(self, time_updated):
        time_updated = time_updated.split(' ')
        n = time_updated[0]
        amount = time_updated[1].replace('s', '')
        current_time = time.time()
        if amount == 'second':
            current_time -= int(n)
        elif amount == 'minute':
            current_time -= int(n) * 60
        elif amount == 'hour':
            current_time -= int(n) * 60 * 60
        elif amount == 'day':
            current_time -= int(n) * 60 * 60 * 24
        elif amount == 'week':
            current_time -= int(n) * 60 * 60 * 24 * 7
        elif amount == 'month':
            current_time -= int(n) * 60 * 60 * 24 * 30
        elif amount == 'year':
            current_time -= int(n) * 60 * 60 * 24 * 30 * 12
        return current_time - 3600

    def main(self):
        self.scrape(first_run=True)
        pass

    def __call__(self):
        self.main()





if __name__ == '__main__':
    scraper = Source()
    scraper()
    pass
