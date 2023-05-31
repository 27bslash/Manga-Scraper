from pprint import pprint
import re
import traceback
import requests
from bs4 import BeautifulSoup
from main import Source


class Reaper(Source):
    def main(self):
        return

    def scrape(self, debug=False):
        # with open('scrapers/test_pages/reaper.html', 'r', encoding="utf-8") as element:
        #     text = element.read()
        #     soup = BeautifulSoup(text, 'html.parser'
        try:
            req = requests.get('https://reaperscans.com/')
        except:
            return []
        text = ''
        if req.status_code != 200:
            print('reaper', req.status_code, 'broken')
            try:
                soup = BeautifulSoup(super().sel(
                    'https://reaperscans.com/'), 'html.parser')
            except:
                print('reaper error', traceback.format_exc())
                return []
        else:
            text = req.text
            soup = BeautifulSoup(text, 'html.parser')

        lst = []
        content = soup.find('div', {'class': 'space-y-4'})
        if content is None:
            print('reaper broken check logs no content')
            with open('reaper_err.txt', 'w', encoding='utf-8') as f:
                f.write(text)
            return lst
        latest_comics = content.find_all(
            'div', {'class': 'focus:outline-none'})
        for element in latest_comics:
            d = {}
            try:
                links = element.find_all('a')
                title = links[0].text
                latest = links[1]

                title = title.strip()
                title = re.sub(r"manhwa", "", title.lower())
                title = super().clean_title(title)

                link = latest.get('href')

                chapter = re.search(r"Chapter (\d+)", latest.text)[1]
                chapter = super().clean_chapter(chapter)

                time_updated = latest.find('p').text
                time_updated = super().convert_time(time_updated.strip())
                if not title or not chapter or not link:
                    continue
                d['title'] = title
                d['latest'] = chapter
                d['type'] = 'reaper'
                d['time_updated'] = time_updated
                d['latest_link'] = link
                d['scansite'] = 'reaperscans'
                d['domain'] = 'https://reaperscans.com'
                lst.append(d)
                if debug:
                    print('reaper', title, chapter, time_updated)
            except Exception as e:
                print('reaper', title, e)
        if len(lst) == 0:
            print('reaper broken check logs')
        return lst

        # print(foc)
        # for item in content:
        #     d = {}
        #     parent = item.parent
        #     # print(parent)
        #     title = item.select('.series-title')[0]
        #     link = parent.select('.series-content')[0].find('a').get('href')
        #     chapter = parent.find('span', {'class': 'series-badge'}).text
        #     time_updated = parent.find('span', {'class': 'series-time'}).text
        #     # ... test
        #     title = title.text.strip()
        #     if re.search(r'\.\.+$', title):
        #         title = self.title_from_link(link)
        #     if title is None:
        #         continue
        #     title = re.sub(r"manhwa", "", title.lower())
        #     title = super().clean_title(title)
        #     # print('title', title.text,title)
        #     time_updated = super().convert_time(time_updated)
        #     # title = super().clean_title(title)
        #     chapter = super().clean_chapter(chapter)
        #     # print(title, chapter, time)
        #     res = self.recursive_parent(parent)
        #     if res:
        #         # print(title, chapter, time)
        #         d['title'] = title
        #         d['latest'] = chapter
        #         d['type'] = 'reaper'
        #         d['time_updated'] = time_updated
        #         d['latest_link'] = link
        #         d['scansite'] = 'reaperscans'
        #         d['domain'] = 'https://reaperscans.com'
        #         lst.append(d)

    def title_from_link(self, link):
        new_title = re.sub(r'\/$', '', link)
        title = re.search(r"(?<=com\/).*(?=\/)", new_title)
        if title:
            title = re.search(r"\/(.*)", title.group(0))
            title = title.group(1).replace('manhwa', '').replace('-', ' ')
            return title
        return None

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
    Reaper().scrape(debug=True)
