import os
import re
import time
import traceback
from pprint import pprint
from turtle import update

import requests
from apscheduler.schedulers.background import BlockingScheduler
from thefuzz import fuzz

from main import Source
from scrapers.asura import Asura
from scrapers.flame import Flame
from scrapers.leviatan import Leviatan
from scrapers.reaper import Reaper
from scrapers.reddit import Reddit_scraper
from scrapers.tcbscans import TcbScraper
from datetime import datetime
from db import db


class Scraper(Source):
    def __init__(self, leviatan, testing):
        self.base_leviatan_url = leviatan
        self.total_manga = []
        self.testing = testing

    def scrape(self, total_manga):
        self.total_manga = total_manga

        curr_urls = db['scans'].find_one({})
        urls = set()

        print(len(total_manga))
        # pprint(total_manga)
        length = len(total_manga)
        scans = self.update_total_manga()
        self.update_users()

        if curr_urls:
            [urls.add(url) for url in curr_urls['urls']]
        scans = urls.union(scans)
        # pprint(manga_list)
        if not self.testing:
            db['scans'].find_one_and_update(
                {}, {'$set': {'urls': list(urls)}}, upsert=True)

    def update_users(self):
        # self.test_search()
        # return
        print('update users')
        for user in db['manga-list'].find({}):
            user_list = user['manga-list']
            user_id = user['user']
            # print('u_id', user_id)
            if user_list:
                self.update_user_list(user_id, user_list)

    def test_search(self):
        for item in self.total_manga:
            for item2 in self.total_manga[::-1]:
                self.fuzzy_search(item['title'], item2['title'])

    def update_user_list(self, user_id, user_list):
        if not self.total_manga:
            import json
            with open('new_list.json', 'r') as f:
                self.total_manga = json.load(f)
        for item in self.total_manga[::-1]:
            for manga in user_list:
                search_res = self.fuzzy_search(manga['title'], item['title'])
                if search_res > 82:
                    # if 'berserk' in item['title']:
                    #     print('debvug')
                    # sys.stdout.write('\x1b[2K')
                    # if 'novel' in item['title']:
                    #     print('debvug')
                    # print(
                    #     f" \r{length - i}/{length} {item['title']} {item['latest']} {item['scansite']}", end='')
                    manga['latest'] = item['sources']['any']['latest']
                    # if 'world-after' in item['title']:
                    #     print('debug')
                    manga['sources'] = self.update_user_sources(
                        manga['sources'], item['sources'])
                    current_source = manga['current_source']
                    curr_source = 'any' if current_source not in manga['sources'] else current_source
                    # print(manga['title'], user_id, manga)
                    manga['read'] = float(
                        manga['sources'][curr_source]['latest']) <= float(manga['chapter'])
                    if not manga['read']:
                        print(
                            f"in {user_id} {item['title']} {manga['title']} {manga['chapter']}/{item['latest']} {item['scansite']} {search_res} 'read: '{manga['read']}")
                        pass
                    break
        if not self.testing:
            db['manga-list'].find_one_and_update(
                {'user': user_id}, {"$set": {f'manga-list': user_list}})
            pass

    def format_title(self, title):
        t1 = re.sub(r'remake', '', title)
        t1 = re.sub(r'\W+', '', t1)
        return t1

    def update_total_manga(self):
        scans = set()
        all_manga = db['all_manga'].find()
        if not self.total_manga:
            import json
            with open('new_list.json', 'r') as f:
                self.total_manga = json.load(f)
        for i, item in enumerate(self.total_manga[::-1]):
            scans.add(item['domain'])
            item['latest_sort'] = float(item['latest'])
            req = db['all_manga'].find_one({'title': item['title']})
            updated = False
            print(
                f"\r {len(self.total_manga) - i}/{len(self.total_manga)}", end='\x1b[1K')
            if req and not self.testing:
                db['all_manga'].find_one_and_update(
                    {'title': item['title']}, {"$set": item})
                updated = True
            elif not updated and req is None:
                for m in all_manga:
                    ratio = fuzz.ratio(item['title'], m['title'])
                    if ratio > 80 and not self.testing:
                        db['all_manga'].find_one_and_update(
                            {'title': m['title']}, {"$set": item}, upsert=True)
                        updated = True
                        break
            if not updated and not self.testing:
                db['all_manga'].find_one_and_update({'title': item['title']}, {
                                                    "$set": item}, upsert=True)
        return scans

    def test_totle_manga(self):
        import json
        with open('new_list.json', 'r') as f:
            total_manga = json.load(f)
        for item in total_manga[::-1]:
            item['latest_sort'] = float(item['latest'])
            req = db['all_manga'].find_one({'title': item['title']})
            updated = False
            if req:
                db['all_manga'].find_one_and_update(
                    {'title': item['title']}, {"$set": item})
                updated = True
            elif not updated and req is None:
                for m in db['all_manga'].find():
                    ratio = fuzz.ratio(item['title'], m['title'])
                    if ratio > 80:
                        db['all_manga'].find_one_and_update(
                            {'title': m['title']}, {"$set": item}, upsert=True)
                        updated = True
            if not updated:
                db['all_manga'].find_one_and_update({'title': item['title']}, {
                                                    "$set": item}, upsert=True)

    def fuzzy_search(self, title, title2):
        fu = fuzz.ratio(self.format_title(title), self.format_title(title2))
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
                            f"{source_list[source]['latest']} < {curr[source]['latest']}", curr[source]['latest_link'])
                        # source_list[source]['latest'] = curr[source]['latest']
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
        db_entry = db['all_manga'].find_one(
            {'title': lst[0]['title']})
        if db_entry:
            for key in db_entry['sources']:
                if key != 'any':
                    db_entry['sources'][key]['scansite'] = key
                    try:
                        new_source = [source
                                      for source in lst if source['scansite'] == key]
                        if new_source:
                            db_entry['sources'][key]['latest'] = new_source[0]['latest']
                            db_entry['sources'][key]['latest_link'] = new_source[0]['latest_link']
                            db_entry['sources'][key]['time_updated'] = new_source[0]['time_updated']
                        lst.append(db_entry['sources'][key])
                    except Exception as e:
                        print(lst, traceback.format_exc())
        try:
            latest_sort = sorted(lst, key=lambda k: (
                float(k['latest']), -k['time_updated']), reverse=True)
            # print(latest_sort)
            d = {}
            # pprint(latest_sort)
            # print('latest', latest_sort[0])

            source_string = {'latest': latest_sort[0]['latest'],
                             'latest_link': latest_sort[0]['latest_link'], 'time_updated': latest_sort[0]['time_updated']}
            d['any'] = source_string

            for item in latest_sort[::-1]:
                source_string = {'latest': item['latest'],
                                 'latest_link':  item['latest_link'], 'time_updated': item['time_updated']}
                try:
                    # pprint(item)
                    d[item['scansite']] = source_string
                except KeyError:
                    print('e', item)
            return d
        except Exception as e:
            print(traceback.format_exc())

    def combine_data(self, first_run=False):
        total_manga = Reddit_scraper(self.base_leviatan_url).main(first_run)
        all_manga = total_manga
        print('leviatan')
        asura = Asura('asurascans').main()
        alpha = Asura('alphascans').main()
        cosmic = Asura('cosmicscans').main()
        luminous = Asura('luminousscans').main()
        leviatan = Leviatan().scrape()
        reaper = Reaper().scrape()
        tcb = TcbScraper().scrape()
        flame = Flame().scrape()
        all_manga += asura + alpha + luminous + leviatan + reaper+tcb+flame+cosmic

        # all_manga += leviatan
        # all_manga = tcb

        # pprint(all_manga)
        all_manga = sorted(
            all_manga, key=lambda k: k['time_updated'], reverse=True)
        return all_manga

    def main(self, first_run=False):
        import json
        os.system('cls')
        if self.testing:
            with open('pre_processed.json', 'r', ) as f:
                data = json.load(f)
        else:
            total_manga = self.combine_data(first_run)
            total_manga = self.combine_series_by_title(total_manga)
            data = total_manga
            with open('pre_processed.json', 'w') as f:
                json.dump(data, f)
            print(len(total_manga))
        try:
            srt = time.perf_counter()
            new_list = []
            for manga in data:
                d = {}
                d = manga[0]
                # print(d['title'])
                d['sources'] = self.update_sources(manga)
                new_list.append(d)
            with open('new_list.json', 'w') as f:
                json.dump(new_list, f)
            self.scrape(new_list)
            print('\ntime taken', time.perf_counter() - srt)
            return new_list
        except Exception as e:
            print(traceback.format_exc())
            with open('err.txt', 'w') as f:
                f.write(str(datetime.now()))
                f.write(traceback.format_exc())


def get_leviatan_url():
    req = requests.get('https://leviatanscans.com/')
    return req.url


def change_leviatan_url(base_url):
    # base_url = 'https://leviatanscans.com/omg'
    lst = db['manga-list'].find({})
    regex = r".*leviatan.*(?=\/manga)"
    for entry in lst:
        user = entry['user']
        manga_list = entry['manga-list']
        for doc in manga_list:
            if 'link' in doc:
                doc['link'] = re.sub(regex, base_url, doc['link'])
            for source in doc['sources']:
                if 'link' in source:
                    source['link'] = re.sub(regex, base_url, source['link'])
                if 'latest_link' in source:
                    source['latest_link'] = re.sub(
                        regex, base_url, source['latest_link'])
                if 'url' in source:
                    source['url'] = re.sub(regex, base_url, source['url'])
        db['manga-list'].find_one_and_update(
            {'user': user}, {"$set": {'manga-list':  manga_list}})


def net_test(retries):
    for i in range(retries):
        try:
            req = requests.get('https://www.google.co.uk/')
            if req.status_code == 200:
                print('connected to the internet')
                return True
            else:
                time.sleep(1)
                continue
        except Exception as e:
            time.sleep(1)
    return False


# scrape(None, False)
if __name__ == '__main__':
    first_run = True
    testing = False
    leviatan_url = 'https://en.leviatanscans.com/home'
    # Scraper(leviatan_url).update_total_manga()
    # Scraper(leviatan_url).main(first_run=first_run)
    if net_test(500):
        if first_run and not testing:
            leviatan_url = get_leviatan_url()
            change_leviatan_url(base_url=leviatan_url)
        scraper = Scraper(leviatan_url, testing)
        scraper.main(first_run=first_run)
        time.sleep(1800)
        scheduler = BlockingScheduler()
        try:
            scheduler.add_job(scraper.main, 'cron', timezone='Europe/London',
                              start_date=datetime.now(), id='scrape',
                              hour='*', minute='*/30', day_of_week='mon-sun')
            scheduler.start()
        except Exception as e:
            print(e, e.__class__)
            scheduler.shutdown()
