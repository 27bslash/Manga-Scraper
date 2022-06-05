import re
import requests
from bs4 import BeautifulSoup
from main import Source


class Reaper(Source):
    def main(self):
        return

    def scrape(self):
        # with open('scrapers/test_pages/reaper.html', 'r', encoding="utf-8") as f:
        #     text = f.read()
        req = requests.get('https://reaperscans.com/')
        if req.status_code != 200:
            print('reaper', req.status_code, 'broken')
            return []
        soup = BeautifulSoup(req.text, 'html.parser')
        content = soup.find_all('div', class_='series-box')
        lst = []
        for item in content:
            d = {}
            parent = item.parent
            # print(parent)
            title = item.select('.series-title')[0]
            link = parent.select('.series-content')[0].find('a').get('href')
            chapter = parent.find('span', {'class': 'series-badge'}).text
            time = parent.find('span', {'class': 'series-time'}).text
            # ... test
            title = super().clean_title(title.text)
            if re.search(r'\.\.+$', title):
                new_title = re.sub(r'\/$', '', link)
                title = re.search(r'[^\/]+$', new_title).group(0)

            # print('title', title.text,title)
            time = super().convert_time(time)
            # title = super().clean_title(title)
            chapter = super().clean_chapter(chapter)
            # print(title, chapter, time)
            res = self.recursive_parent(parent)
            if res:
                # print(title, chapter, time)
                d['title'] = title
                d['latest'] = chapter
                d['type'] = 'reaper'
                d['time_updated'] = time
                d['link'] = link
                d['scansite'] = 'reaperscans'
                d['domain'] = 'https://reaperscans.com'
                lst.append(d)
            else:
                break
        return lst

    def recursive_parent(self, element) -> bool:
        if element.parent.attrs['class'] == ['latest']:
            return True
        elif element.parent.name == 'section' and element.parent.attrs['class'] is not ['latest'] is None or element.parent.name == 'body':
            return False
        else:
            return self.recursive_parent(element.parent)

    def __call__(self):
        return self.scrape()


if __name__ == "__main__":
    Reaper().scrape()
