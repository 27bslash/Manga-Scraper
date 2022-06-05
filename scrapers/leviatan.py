from pprint import pprint
import re
import requests
from bs4 import BeautifulSoup
from main import Source


class Leviatan(Source):
    def main(self):
        req = requests.get('https://leviatanscans.com')
        print(req.status_code)
        # with open('scrapers/test_pages/leviatan.html', 'w', encoding="utf-8") as f:
        #     f.write(req.text)
        # pass

    def scrape(self):
        # self.main()
        # with open('scrapers/test_pages/leviatan.html', 'r', encoding="utf-8") as f:
        #     text = f.read()
        lst = []
        title_list = []
        req = requests.get('https://leviatanscans.com')
        if req.status_code != 200:
            print('leviatan', req.status_code, 'broken')
            return []
        else:
            text = req.text
            
        # with open('scrapers/leviatan.html', 'w', encoding="utf-8") as f:
        #     f.write(text)
        # with open('scrapers/test_pages/leviatan.html', 'r', encoding="utf-8") as f:
        #     text = f.read()
        soup = BeautifulSoup(text, 'html.parser')
        chapters = soup.select('div[class*="chapter-item"]')
        titles = soup.select('div[class*="post-title"]')
        item_summary = soup.select('div[class*="item-summary"]')
        for item in item_summary:
            d = {}
            title_el = item.find("div", "post-title").find('a').text
            title = super().clean_title(title_el)
            chapter_el = item.find('div', 'chapter-item')
            chapter = super().clean_chapter(chapter_el.find('span').text)
            link_el = chapter_el.find('a').get('href')
            try:
                a_tags = chapter_el.find_all('a')
                for tag in a_tags:
                    if tag.has_attr('title'):
                        time_el = tag.attrs['title']
                        break
                time_updated = super().convert_time(time_el)
                d['type'] = 'leviatan'
                d['title'] = title
                d['latest'] = chapter
                d['link'] = link_el
                d['time_updated'] = time_updated
                d['scansite'] = 'leviatanscans'
                d['domain'] = 'https://leviatanscans.com'
                # pprint(d)
                lst.append(d)
            except Exception as e:
                print(title, chapter_el, e)

        return lst
        # print(lst)
        # for card in titles:
        #     link = card.find_all('a')
        #     print(link)
        # chapter =

    def __call__(self):
        return self.scrape()


if __name__ == "__main__":
    s = Leviatan()
    s()
