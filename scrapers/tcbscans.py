import requests
from bs4 import BeautifulSoup
import re
import time
import datetime


class TcbScraper():
    def main(self):
        req = requests.get('https://onepiecechapters.com/')
        # print(req.status_code, req.text)
        with open('scrapers/tcb.html', 'w', encoding="utf-8") as f:
            print(req.status_code)
            f.write(req.text)
        pass

    def scrape(self):
        link_regex = r"[^\/]+$"
        title_regex = r".*(?=-chapter)"
        chapter_regex = r"(?<=chapter-)\d*\.?\d+"
        # with open('scrapers/test_pages/tcb.html', 'r', encoding="utf-8") as f:
        #     text = f.read()
        req = requests.get('https://onepiecechapters.com/')
        if req.status_code != 200:
            print('tcbscasn', req.status_code, 'broken')
        soup = BeautifulSoup(req.text, 'html.parser')
        cards = soup.select('div[class*="bg-card"]')
        lst = []
        for card in cards:
            link = card.find('a')
            url = link.get('href')
            url = f"https://onepiecechapters.com{url}"
            d = {}
            try:
                path = re.search(link_regex, url).group(0)
                title = re.search(title_regex, path).group(0)
                chapter = re.search(chapter_regex, path).group(0)

                d['type'] = 'tcb'
                d['time_updated'] = time.time()-self.seconds_since_update()
                d['title'] = title
                d['latest'] = chapter
                d['domain'] = 'https://onepiecechapters.com/'
                d['link'] = url
                d['scansite'] = 'tcbscans'
                lst.append(d)
            except TypeError:
                print(url)
                continue
        # print(lst)
        return lst

    def seconds_since_update(self):
        today = datetime.datetime.today().weekday()
        days_since_thursday = 7 - (3 - today) % 7
        if today == 2:
            return 0
        else:
            return 86400 * days_since_thursday

    def __call__(self):
        return self.scrape()


t = TcbScraper()
t()
