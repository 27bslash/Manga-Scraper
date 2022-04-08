from multiprocessing import connection
import praw
import re
from pprint import pprint
import pymongo
import os
from dotenv import load_dotenv
import time
load_dotenv()

connection = os.environ['DB_CONNECTION']
cluster = pymongo.MongoClient(
    f"{connection}?retryWrites=true&w=majority")
db = cluster['manga-scraper']

#
# TODO
# scrape reddit on timer
# check manga db for user if it matches notify somehow
# if user goes on site update counter
# have some kind of overview on a chrome extension
#


def scrape():
    curr_urls = db['scans'].find_one({})
    urls = set()
    total_manga = get_todays_list()

    for user in db['manga-list'].find({}):
        user_list = []
        # testing purposes
        if user['user'] == 'all_manga':
            continue
        # print(user)
        if not user['manga-list']:
            # print(user['user'])
            pass
        for item in total_manga:
            # pprint(item)
            for i, manga in enumerate(user['manga-list']):
                if item['title'] == manga['title']:
                    if item['latest'] > manga['chapter']:
                        manga['read'] = False
                        manga['sources'] = update_sources(
                            item['scansite'], manga)
                        # this will run every time make it update only once
                        manga['updated'] = time.time()
                        manga['latest'] = item['latest']
                        manga['link'] = item['link']
                        manga['domain'] = item['domain']
                        manga['test'] = True
            
                db['manga-list'].find_one_and_update({'user': 'all_manga'},
                                                    {"$set": {f'manga-list.{i}': manga}})
        print(user['user'], time.time())
        # update manga in db

    if curr_urls:
        [urls.add(url) for url in curr_urls['urls']]
    # pprint(manga_list)
    db['scans'].find_one_and_update(
        {}, {'$set': {'urls': list(urls)}}, upsert=True)


def update_sources(scansite, manga):
    if 'sources' not in manga:
        manga['sources'] = []
    if scansite not in manga['sources']:
        manga['sources'].append(scansite)
    return manga['sources']


def get_domain_from_self_post(submission, title, chapter_num):
    banned_domains = ['alpha', 'leviatan', 'reaper', 'luminous']
    for name in banned_domains:
        if name in submission.title.lower():
            title = title.replace(' ', '-')
            if name == 'reaper':
                url = f"https://reaperscans.com/series/{title}/chapter-{chapter_num}/"
            elif name == 'leviatan':
                url = f"https://leviatanscans.com/manga/{title}/{chapter_num}/"
            elif name == 'luminous':
                url = f"https://luminousscans.com/{title}-chapter-{chapter_num}/"
            elif name == 'alpha':
                url = f"https://alpha-scans.org/{title}-chapter-{chapter_num}"
            return url
    return None


def get_todays_list():
    title_regex = r"(?<=\[DISC\]).*(?= \(?ch|ep|chapter)"
    reddit = praw.Reddit(
        client_id="wEBZeE2Bh10Ki1kCrchhKQ",
        client_secret="XBQQVa1bfXj1I2vqzAgncn4B3yjUUg",
        user_agent="manga scraper by u/27bslash",
    )
    manga_list = []
    for i, submission in enumerate(reddit.subreddit("manga").new(limit=100)):
        d = {}
        if '[DISC]' in submission.title:
            title = re.findall(
                title_regex, submission.title, re.IGNORECASE)
            if title:
                title = re.sub(r"\s?\-\s?$", '', title[0])
                title = title.strip().lower()
            else:
                continue
            chapter_num = get_chapter_number(submission.title)
            # print(submission.url)
            if 'reddit' not in submission.url:
                # continue
                domain = extract_domain(submission.url)
                url = submission.url
                if 'cubari' in submission.url:
                    scan_site = get_scans(title=submission.title)
                    url = get_domain_from_self_post(
                        submission=submission, title=title, chapter_num=chapter_num)
                    domain = extract_domain(url)
                if domain:
                    scan_site = get_scans(url=domain)
                else:
                    continue
                # check_if_in_db(submission.url)
            elif 'reddit' in submission.url:
                # print(submission.title)
                url = get_domain_from_self_post(
                    submission, title, chapter_num)
                domain = extract_domain(url)
                # domain = extract_domain(submission.url)
                if domain:
                    scan_site = get_scans(url=domain)
                continue
                # db['todays-manga'].find_one_and_update({}, {})
            d['title'] = title.replace(' ', '-')
            d['latest'] = chapter_num
            d['domain'] = domain
            d['link'] = url
            d['scansite'] = scan_site
            manga_list.append(d)
    return manga_list


def get_chapter_number(title):
    matches = re.findall(r"\d+\.?\d*", title)
    if matches:
        match = matches[len(matches)-1]
        res = re.sub(r"^0+", '', match)
        return res
    else:
        return -1


def update_all():
    for user in db['manga-list'].find({}):
        add_field_to_manga(user, 'sources', [])


def add_field_to_manga(user, field, value):
    for manga in user['manga-list']:
        manga[field] = value
    db['manga-list'].find_one_and_update({'user': user['user']},
                                         {"$set": {'manga-list': user['manga-list']}}, upsert=True)


def get_scans(title=None, url=None):
    # scan_regex = "[a-z-]*(?=\.)"
    if title:
        title = title.replace("[DISC]", '')
        # extract scans from [] () or after | symbol
        scan_regex = r"\[.*\]|\(.*\)|(?=\|).*|"
        scan_site = re.findall(scan_regex, title, re.IGNORECASE)
        scan_site = [str for str in scan_site if len(str) > 0]
        if len(scan_site) > 0 and 'cubari' not in title.lower():
            scan_site = re.sub(r"[\]\[\(\)\|\s]", '',
                               scan_site[0]).strip().lower()
            return scan_site
        return None
    url = re.sub(r'viewer|reader', '', url)
    if url:
        scan_regex = "[a-z-]*(?<!www)(?=\.)"
        scanSite = re.findall(scan_regex, url, re.IGNORECASE)[0]
    return scanSite


def check_if_in_db(manga, latest, scan=None):
    # user = 'test'
    # manga has curr ch , title,scansite and link fields
    curr_chapter = float(manga['chapter'])
    # print(manga['scan'])
    scan = manga['scansite']
    return curr_chapter < float(latest)


def extract_domain(url):
    if not url:
        return
    regex = r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/?\n]+)"
    try:
        return re.search(regex, url).group()
    except Exception as e:
        print(url, e, e.__class__)


def main():
    scrape()


if __name__ == '__main__':
    main()
