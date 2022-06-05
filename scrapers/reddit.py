import praw
import re
from pprint import pprint
import pymongo
import os
import time
from dotenv import load_dotenv
import requests


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


class Reddit_scraper():
    def __init__(self, leviatan) -> None:
        self.base_leviatan_url = leviatan
        self.banned_domains = [
            'alpha', 'leviatan', 'reaper', 'luminous', 'flame', 'asura']

    def get_url(self, submission, title, chapter_num):
        if submission.selftext:
            if 'http' in submission.selftext:
                # print('self text', submission.selftext)
                return self.get_domain_from_self_post(submission, title, chapter_num)
            else:
                return self.get_banned_domains(submission, title, chapter_num)
        elif 'reddit' in submission.url or 'cubari' in submission.url:
            return self.get_banned_domains(submission, title, chapter_num)
        else:
            return submission.url

    def get_domain_from_self_post(self, submission, title, chapter_num):
        self_text_html = submission.selftext_html
        link_regex = r"(?<=href=\").*?(?=\")"
        link = re.findall(link_regex, self_text_html)
        if link:
            return link[0]
        else:
            return self.banned_urls(submission.selftext.lower(), title, chapter_num)

    def get_banned_domains(self, submission, title, chapter_num):
        banned_domains = ['alpha', 'leviatan', 'reaper', 'luminous']
        for name in banned_domains:
            if name in submission.title.lower() or name in submission.selftext.lower():
                title = title.replace(' ', '-')
                return self.banned_urls(name, title, chapter_num)
        return None

    def banned_urls(self, name, title, chapter_num):
        title = title.replace('\'', '')
        title = re.sub(r"–", '-', title)
        title = re.sub(r"-+", '-', title)
        if 'reaper' in name:
            url = f"https://reaperscans.com/series/{title}/chapter-{chapter_num}/"
        elif 'leviatan' in name:
            url = f"{self.base_leviatan_url}/manga/{title}/{chapter_num}/"
        elif 'luminous' in name:
            url = f"https://luminousscans.com/{title}-chapter-{chapter_num}/"
        elif 'alpha' in name:
            url = f"https://alpha-scans.org/{title}-chapter-{chapter_num}"
        elif 'flame' in name:
            url = f"https://flamescans.org/{title}-chapter-{chapter_num}"
        elif 'asura' in name:
            url = f"https://asurascans.com/{title}-chapter-{chapter_num}"
        return url

    def get_title(self, submission, testing=False):
        title_regex = r"(?<=\[DISC\]).*?(?= \(?ch|ep|chapter)"
        if testing:
            base_title_string = submission
        else:
            base_title_string = submission.title
        title = re.findall(
            title_regex, base_title_string, re.IGNORECASE)
        if title:
            title = re.sub(r"\s?\-\s?$", '', title[0])
            title = re.sub(r"::", '', title)
            title = title.replace('(', '')
            title = title.replace(')', '')
            title = title.replace('&', 'and')
            title = title.strip().lower()
            title = title.replace(' ', '-').replace('’', '\'')
            title = title.replace('---', '-')
            return title
        else:
            return None

    def get_scans(self, title=None, url=None):
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
                return scan_site.replace('-', '')
            return None
        url = re.sub(r'viewer|reader', '', url)
        if url:
            scan_regex = "\w+-?\w+(?<!www)(?=\.)"
            scan_site = re.findall(scan_regex, url, re.IGNORECASE)[0]
            return scan_site.replace('-', '')

    def get_banned_domain(self, scan_site):
        if scan_site == 'alpha':
            return 'alpha-scans.org'
        elif scan_site == 'leviatan':
            return 'leviatan-scans.com'
        elif scan_site == 'reaper':
            return 'reaperscans.com'
        elif scan_site == 'luminous':
            return 'luminousscans.com'
        elif scan_site == 'flame':
            return 'flamescans.org'
        return
    def get_todays_list(self, first_run=False):
        reddit = praw.Reddit(
            client_id="wEBZeE2Bh10Ki1kCrchhKQ",
            client_secret="XBQQVa1bfXj1I2vqzAgncn4B3yjUUg",
            user_agent="manga scraper by u/27bslash",
        )
        manga_list = []
        submissions = []
        limit = 50
        if first_run:
            limit = None

        for submission in reddit.subreddit("manga").search('flair:"DISC"', sort='hot', limit=limit):
            submissions.append(submission)
        for submission in submissions[::-1]:
            d = {}
            if '[DISC]' in submission.title:
                title = self.get_title(submission)
                if not title:
                    # print('no title/', submission.title)
                    continue

                chapter_num = self.get_chapter_number(submission.title)
                # print(submission.url)
                domain = submission.domain
                if 'i.redd' in domain:
                    continue
                elif 'cubari' in domain:
                    # print(submission.title, domain)
                    scan_site = self.get_scans(title=submission.title)
                    # print('scan site', scan_site)
                    url = self.get_url(
                        submission=submission, title=title, chapter_num=chapter_num)
                    # print('url', url)
                    # print('link post', title, url)
                    # print('domain', domain)
                    if url:
                        domain = self.extract_domain(url)
                        # print('domain2', domain)
                    else:
                        continue
                elif 'reddit.com' in domain:
                    # print('reddit', title)
                    url = submission.url
                    # print(vars(submission))
                    # weird self post comment redirect'
                    if 'comments' in submission.url:
                        url = re.sub(r"\/$", '', submission.url)
                        search = re.search(r"[^\/]+$", url, re.IGNORECASE)
                        subm = reddit.submission(id=search.group(0))
                        domain = subm.domain
                        if domain and 'reddit' not in domain:
                            url = self.get_url(
                                subm, title, chapter_num)
                    domain = self.extract_domain(url)
                    if domain and 'reddit' not in domain and 'twitter' not in domain and 'cubari' not in domain:
                        scan_site = self.get_scans(url=domain)
                        print(title, scan_site, url, domain)
                    else:
                        print(title, 'no domain', chapter_num)
                        continue
                else:
                    url = submission.url
                    scan_site = self.get_scans(url=domain)
                d['type'] = 'reddit'
                d['time_updated'] = submission.created_utc
                d['title'] = title
                d['latest'] = chapter_num
                d['domain'] = domain
                d['link'] = url
                d['scansite'] = scan_site
                # print(d)
                # d['sources'] = super().update_sources(d, scan_site, d)
                manga_list.append(d)
        return manga_list

    def extract_domain(self, url):
        if not url:
            return
        regex = r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/?\n]+)"
        try:
            return re.search(regex, url).group()
        except Exception as e:
            print(url, e, e.__class__)

    def get_chapter_number(self, submission):
        chapter_regex = r".*(?<=chapter|episode)|.*(?<=ch|ep)"
        title = submission.title
        matches = re.findall(chapter_regex, title, re.IGNORECASE)
        if 'webtoons' in submission.url:
            match = re.search(r"(?<=episode_no=).*", submission.url)
            if match:
                return match.group()
        if matches:
            match = matches[0]
            rep = title.replace(match, '')
            pot_chapters = re.findall(r"(?<=[\W])\d*\.?\d+", rep)
            pot_chapters = sorted(pot_chapters, key=float, reverse=True)
            if not pot_chapters:
                return None
            chapter_num = pot_chapters[0]
            chapter_num = re.sub(r"^0+", '', chapter_num)
            chapter_num = re.sub(r"^\W+", '', chapter_num)
            return chapter_num

    def main(self, first_run=False):
        return self.get_todays_list(first_run)


def update_all():
    for user in db['manga-list'].find({}):
        add_field_to_manga(user, 'o', time.time())
        # add_field_to_manga(user, 'time_updated', 0)
    for doc in db['all_manga'].find({}):
        for k in doc['sources']:
            doc['sources'][k]['time_updated'] = time.time()
        db['all_manga'].find_one_and_update({'_id': doc['_id']}, {"$set": doc})


def add_field_to_manga(user, field, value):
    for manga in user['manga-list']:
        for k in manga['sources']:
            manga['sources'][k]['time_updated'] = value
    db['manga-list'].find_one_and_update({'user': user['user']},
                                         {"$set": {'manga-list': user['manga-list']}}, upsert=True)


def get_leviatan_url():
    req = requests.get('https://leviatanscans.com/')
    print(req.url)
    return req.url


def add_current_source():
    lst = db['manga-list'].find_one({})
    for doc in lst['manga-list']:
        doc['current_source'] = 'any'
    db['manga-list'].find_one_and_update(
        {'user': '1649438609702'}, {"$set": lst})


def change_leviatan_url():
    base_url = get_leviatan_url()
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
        print(doc['sources']['any']['url'])
    db['manga-list'].find_one_and_update(
        {'user': '1649438609702'}, {"$set": lst})


if __name__ == '__main__':
    Reddit_scraper('test').get_todays_list(True)
