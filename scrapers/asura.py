from bs4 import BeautifulSoup
import requests
from main import Source


class Asura(Source):
    def __init__(self, site) -> None:
        self.site = site
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36"}

    def main(self):
        # with open('scrapers/test_pages/luminous.html', 'w', encoding="utf-8") as f:
        #     f.write(requests.get('https://luminousscans.com/',
        #             headers=self.headers).text)

        # with open(f'scrapers/test_pages/{self.site}.html', 'r', encoding="utf-8") as f:
        if self.site == 'alphascans':
            rq = requests.get('https://alpha-scans.org/',
                              headers=self.headers)

        else:
            rq = requests.get('https://luminousscans.com/',
                              headers=self.headers)
        if rq.status_code == 200:
            soup = BeautifulSoup(rq.text, 'html.parser')
        else:
            print(self.site, rq.status_code, 'broken')
            return []
        latest_updates = soup.find_all('div', class_='luf')
        lst = []
        for update in latest_updates:
            d = {}
            try:
                title = update.find('a').text
                chapter_obj = update.find("ul").find("li")
                chapter_link = chapter_obj.find("a")
                chapter = chapter_link.text.replace('Chapter ', '')
                link = chapter_link.get('href')
                time_updated = chapter_obj.find('span').text
                d['title'] = super().clean_title(title)
                d['latest'] = super().clean_chapter(chapter)
                d['link'] = link
                d['time_updated'] = super().convert_time(time_updated)
                d['scansite'] = self.site
                if self.site == 'alphascans':
                    d['domain'] = 'https://alpha-scans.org'
                else:
                    d['domain'] = 'https://luminousscans.com'
                lst.append(d)
            except Exception as e:
                print(e, self.site, update)
        return lst

    def __call__(self):
        return self.main()


if __name__ == "__main__":
    s = Asura()
    s()
