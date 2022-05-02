import datetime
from distutils.command.build_scripts import first_line_re
import os
import sys
import time
from pprint import pprint
import requests
import pymongo
from apscheduler.schedulers.background import BlockingScheduler
from dotenv import load_dotenv

from main import Source
from scrapers.asura import Asura
from scrapers.leviatan import Leviatan
from scrapers.reaper import Reaper
from scrapers.reddit import Reddit_scraper

load_dotenv()
connection = os.environ['DB_CONNECTION']
cluster = pymongo.MongoClient(
    f"{connection}?retryWrites=true&w=majority")
db = cluster['manga-scraper']


class Scraper(Source):
    def __init__(self, leviatan):
        self.base_leviatan_url = leviatan

    def scrape(self, total_manga):
        srt = time.perf_counter()
        curr_urls = db['scans'].find_one({})
        urls = set()

        print(len(total_manga))
        # pprint(total_manga)
        length = len(total_manga)
        for user in db['manga-list'].find({}):
            user_list = []
            # testing purposes
            if user['user'] == 'all_manga':
                continue
            # print(user)
            if not user['manga-list']:
                # print(user['user'])
                pass
            user_list = user['manga-list']
            for i, item in enumerate(total_manga):
                # print(item['link'])
                sys.stdout.write(f"\r{length - i}/{length}")
                sys.stdout.flush()
                for i, manga in enumerate(user_list):
                    # print(item['title'], manga['title'])
                    if item['title'] == manga['title']:
                        print('\nin', item['title'])
                        # manga = super().update_manga_dict(
                        #     manga, item)
                        break
                strt = time.perf_counter()
                db['all_manga'].find_one_and_update(
                    {'title': item['title']}, {"$set": item}, upsert=True)
                # print(time.perf_counter() - strt, 'seconds')
            db['manga-list'].find_one_and_update(
                {'user': user['user']}, {"$set": {f'manga-list': user_list}})
            print(user['user'], '\ntime taken', time.perf_counter() - srt)
            # pprint(total_manga)
            # update manga in db

        if curr_urls:
            [urls.add(url) for url in curr_urls['urls']]
        # pprint(manga_list)
        db['scans'].find_one_and_update(
            {}, {'$set': {'urls': list(urls)}}, upsert=True)

    def combine_data(self, first_run=False):
        total_manga = Reddit_scraper(self.base_leviatan_url).main(first_run)
        now = datetime.datetime.now()
        all_manga = total_manga
        t = now.minute - 30
        if t <= 5 and t >= 0 or first_run:
            print('leviatan')
            alpha = Asura('alphascans')()
            luminous = Asura('luminousscans')()
            leviatan = Leviatan()()
            reaper = Reaper()()
            all_manga += alpha + luminous + leviatan + reaper
        # all_manga = total_manga + leviatan + alpha + reaper+luminous
        all_manga = sorted(
            all_manga, key=lambda k: k['time_updated'], reverse=True)
        return all_manga

    def list_dupes(self, lst):
        ret = []
        seen = set()
        # lst = sorted(lst, key=lambda k: k['time_updated'], reverse=True)
        for x in lst:
            title = x['title']
            if title not in seen:
                l = [item for item in lst if item['title'] == title]
                ret.append(l)
            seen.add(title)
        return ret

    def main(self, first_run=False):
        total_manga = self.combine_data(first_run)
        print(len(total_manga))
        total_manga = self.list_dupes(total_manga)
        print(len(total_manga))
        new_list = []
        for manga in total_manga:
            d = {}
            d = manga[0]
            d['sources'] = self.update_sources(manga)
            # pprint(d)
            new_list.append(d)
            # break
        pprint(new_list)

        self.scrape(new_list)
        return new_list

    def update_sources(self, lst):
        # print('l', lst)
        # takes a list of dupes and makes a list of sources
        db_entry = db['all_manga'].find({'title': lst[0]['title']})
        db_res = [entry for entry in db_entry]
        if len(db_res) > 0:
            lst += db_res
        latest_sort = sorted(lst, key=lambda k: (
            k['latest'], -k['time_updated']), reverse=True)
        # print(latest_sort)
        d = {}
        # print('latest', latest_sort[0])
        source_string = {'url': latest_sort[0]['link'], 'latest': latest_sort[0]['latest'],
                         'latest_link': latest_sort[0]['link'], 'time_updated': latest_sort[0]['time_updated']}
        d['any'] = source_string
        for item in latest_sort:
            source_string = {'url': item['link'], 'latest': item['latest'],
                             'latest_link': item['link'], 'time_updated': item['time_updated']}
            try:
                d[item['scansite']] = source_string
            except KeyError:
                print('e', item)
        return d


def get_leviatan_url():
    req = requests.get('https://leviatanscans.com/')
    return req.url


# scrape(None, False)
if __name__ == '__main__':
    first_run = False
    leviatan_url = 'https://leviatanscans.com/fux'
    if first_run:
        leviatan_url = get_leviatan_url()
    scraper = Scraper(leviatan_url)
    scraper.main(first_run)
    # change_leviatan_url()
    scheduler = BlockingScheduler()
    try:
        scheduler.add_job(scraper.main, 'cron', timezone='Europe/London',
                          start_date=datetime.datetime.now(), id='scrape',
                          hour='*', minute='*/5', day_of_week='mon-sun')
        # scheduler.start()
    except Exception as e:
        print(e, e.__class__)
        scheduler.shutdown()
