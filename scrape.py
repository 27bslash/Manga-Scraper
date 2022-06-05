import datetime
import os
import re
import time
import traceback
from thefuzz import fuzz

import pymongo
import requests
from apscheduler.schedulers.background import BlockingScheduler
from dotenv import load_dotenv

from main import Source
from scrapers.asura import Asura
from scrapers.leviatan import Leviatan
from scrapers.reaper import Reaper
from scrapers.reddit import Reddit_scraper
from scrapers.tcbscans import TcbScraper

load_dotenv()
connection = os.environ['DB_CONNECTION']
cluster = pymongo.MongoClient(
    f"{connection}?retryWrites=true&w=majority")
db = cluster['manga-scraper']


class Scraper(Source):
    def __init__(self, leviatan):
        self.base_leviatan_url = leviatan
        self.total_manga = []

    def scrape(self, total_manga):
        self.total_manga = total_manga

        curr_urls = db['scans'].find_one({})
        urls = set()

        print(len(total_manga))
        # pprint(total_manga)
        length = len(total_manga)

        self.update_users()
        

        if curr_urls:
            [urls.add(url) for url in curr_urls['urls']]
        # pprint(manga_list)
        db['scans'].find_one_and_update(
            {}, {'$set': {'urls': list(urls)}}, upsert=True)

    def update_users(self):
        # self.test_search()
        # return
        for user in db['manga-list'].find({}):
            user_list = user['manga-list']
            user_id = user['user']
            self.update_user_list(user_id, user_list)

    def test_search(self):
        for item in self.total_manga:
            for item2 in self.total_manga[::-1]:
                self.fuzzy_search(item['title'], item2['title'])

    def update_user_list(self, user_id, user_list):
        for item in self.total_manga[::-1]:
            db['all_manga'].find_one_and_update(
                {'title': item['title']}, {"$set": item}, upsert=True)
            for manga in user_list:
                search_res = self.fuzzy_search(item['title'], manga['title'])
                if search_res > 80:
                    # sys.stdout.write('\x1b[2K')
                    # print(
                    #     f" \r{length - i}/{length} {item['title']} {item['latest']} {item['scansite']}", end='')
                    print('\nin', user_id, item['title'],
                          item['latest'], item['scansite'], search_res)
                    # pprint(manga)
                    manga['latest'] = item['sources']['any']['latest']
                    manga['sources'] = self.update_user_sources(
                        manga['sources'], item['sources'])
                    # if 'tower' in item['title']:
                    #     # pprint(manga)
                    #     pass

                    # if 'great' in item['title']:
                    #     print('debug')
                    manga['read'] = manga['latest'] <= manga['chapter']
                    break
        db['manga-list'].find_one_and_update(
            {'user': user_id}, {"$set": {f'manga-list': user_list}})

    def update_total_manga(self, total_manga):
        for i, item in enumerate(total_manga[::-1]):
            # print(item['link'])
            print(f" \r{length - i}/{length}", flush=True, end='')
            # print('\nin', item['title'],
            #               item['latest'], item['scansite'])
            # self.update_user_list(item['user'], item)
            db['all_manga'].find_one_and_update(
                {'title': item['title']}, {"$set": item}, upsert=True)
        pass

    def fuzzy_search(self, title, title2):
        fu = fuzz.ratio(title,
                        title2)
        return fu

    def text_similarity(self, title, title2):
        title_split = title.split('-')
        title_split2 = title2.split('-')
        if title_split == title_split2:
            return True
        ite = title_split
        sub = title_split2
        if len(title_split) < len(title_split2):
            ite = title_split2
            sub = title_split
        ret = len([word for word in ite if word not in sub])
        ret = ret/len(ite)
        return ret <= 0.25

    def update_user_sources(self, curr: dict, source_list: dict) -> dict:
        d = {}
        combined_sources = [source_list, curr]
        for source in source_list:
            try:
                if source in curr:
                    if 'url' in curr[source]:
                        source_list[source]['url'] = curr[source]['url']
                    if float(source_list[source]['latest']) < float(curr[source]['latest']):
                        print(
                            f"{source_list[source]['latest']} < {curr[source]['latest']}")
                        source_list[source]['latest'] = curr[source]['latest']
            except Exception as e:
                print(traceback.format_exc(),
                      source_list[source]['latest_link'], curr[source])
        return source_list

    def combine_series_by_title(self, lst):
        ret = []
        seen = set()
        # lst = sorted(lst, key=lambda k: k['time_updated'], reverse=True)
        for item in lst:
            title = item['title']
            if title not in seen:
                l = [x for x in lst if self.text_similarity(x['title'], title)]
                ret.append(l)
            seen.add(title)
        return ret

    def update_sources(self, lst):
        # print('l', lst)
        # takes a list of dupes and makes a list of sources
        db_entry = db['all_manga'].find({'title': lst[0]['title']})
        db_res = [entry for entry in db_entry]
        if len(db_res) > 0:
            lst += db_res
        # pprint(lst)
        latest_sort = sorted(lst, key=lambda k: (
            k['latest'], -k['time_updated']), reverse=True)
        # print(latest_sort)
        d = {}
        # pprint(latest_sort)
        # print('latest', latest_sort[0])
        source_string = {'latest': latest_sort[0]['latest'],
                         'latest_link': latest_sort[0]['link'], 'time_updated': latest_sort[0]['time_updated']}
        d['any'] = source_string
        if d['any']['latest'] == '133':
            print(d['any'])
        for item in latest_sort[::-1]:
            source_string = {'latest': item['latest'],
                             'latest_link': item['link'], 'time_updated': item['time_updated']}
            try:
                # pprint(item)
                d[item['scansite']] = source_string
            except KeyError:
                print('e', item)
        return d

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
            tcb = TcbScraper()()
            all_manga += alpha + luminous + leviatan + reaper+tcb
            # all_manga += leviatan
            # all_manga += tcb
        # pprint(all_manga)
        all_manga = sorted(
            all_manga, key=lambda k: k['time_updated'], reverse=True)
        return all_manga

    def main(self, first_run=False):
        srt = time.perf_counter()
        total_manga = self.combine_data(first_run)
        # print(len(total_manga))
        total_manga = self.combine_series_by_title(total_manga)
        # pprint(total_mang/a)
        print(len(total_manga))
        new_list = []
        for manga in total_manga:
            d = {}
            d = manga[0]
            # print(manga)
            d['sources'] = self.update_sources(manga)
            # print(d['sources'])
            # pprint(d)
            new_list.append(d)
            # break
        self.scrape(new_list)
        print('\ntime taken', time.perf_counter() - srt)
        return new_list


def get_leviatan_url():
    req = requests.get('https://leviatanscans.com/')
    return req.url


def change_leviatan_url(base_url):
    # base_url = 'https://leviatanscans.com/omg'
    lst = db['manga-list'].find_one({})
    regex = r".*leviatan.*(?=\/manga)"
    for doc in lst['manga-list']:
        if 'leviatan' in doc['link']:
            doc['link'] = re.sub(regex, base_url, doc['link'])
        if 'leviatan' in doc['sources']:
            source = doc['sources']['leviatan']
            source['url'] = re.sub(
                regex, base_url, source['url'])
            source['latest_link'] = re.sub(
                regex, base_url, source['url'])

        if 'leviatan' in doc['sources']['any']['url']:
            source = doc['sources']['any']
            source['url'] = re.sub(
                regex, base_url, source['url'])
            source['latest_link'] = re.sub(
                regex, base_url, source['latest_link'])
        # print(doc['sources']['any']['url'])
    db['manga-list'].find_one_and_update(
        {'user': '1649438609702'}, {"$set": lst})


# scrape(None, False)
if __name__ == '__main__':
    first_run = True
    leviatan_url = 'https://leviatanscans.com/atg'
    if first_run and 1 == 2:
        leviatan_url = get_leviatan_url()
        change_leviatan_url(base_url=leviatan_url)
    scraper = Scraper(leviatan_url)
    scraper.main(first_run)
    scheduler = BlockingScheduler()
    try:
        scheduler.add_job(scraper.main, 'cron', timezone='Europe/London',
                          start_date=datetime.datetime.now(), id='scrape',
                          hour='*', minute='*/5', day_of_week='mon-sun')
        # scheduler.start()
    except Exception as e:
        print(e, e.__class__)
        scheduler.shutdown()
