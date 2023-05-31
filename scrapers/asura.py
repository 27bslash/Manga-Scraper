import traceback
from bs4 import BeautifulSoup
import requests
from main import Source
import re


class Asura(Source):
    def __init__(self, site) -> None:
        self.site = site
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36"}

    def main(self, debug=False):
        # with open('scrapers/test_pages/luminous.html', 'w', encoding="utf-8") as f:
        #     f.write(requests.get('https://luminousscans.com/',
        #             headers=self.headers).text)

        # with open(f'scrapers/test_pages/{self.site}.html', 'r', encoding="utf-8") as f:
        if self.site == 'alphascans':
            url = 'https://alpha-scans.org/'
        if self.site == 'cosmicscans':
            url = 'https://cosmicscans.com/'
        elif self.site == 'asurascans':
            url = 'https://www.asurascans.com/'
        else:
            url = 'https://luminousscans.com/'
        try:
            rq = requests.get(url, headers=self.headers)
        except:
            return []
        if rq.status_code == 200:
            soup = BeautifulSoup(rq.text, 'html.parser')
        else:
            print('selenium', url)
            try:
                soup = BeautifulSoup(super().sel(url), 'html.parser')
            except:
                print(traceback.format_exc())
                return []
        latest_updates = soup.find_all('div', class_='luf')
        lst = []
        for update in latest_updates:
            d = {}
            try:
                title = update.find('a').text
                if 'raw' in title.lower():
                    continue
                chapter_obj = update.find("ul").find("li")
                chapter_link = chapter_obj.find("a")
                chapter = chapter_link.text
                link = chapter_link.get('href')
                time_updated = chapter_obj.find('span').text
                if not title or not chapter or not link:
                    continue
                d['title'] = super().clean_title(title)
                d['latest'] = re.search(
                    r"\d+", super().clean_chapter(chapter)).group(0)
                d['latest_link'] = link
                d['time_updated'] = super().convert_time(time_updated)
                d['scansite'] = self.site
                d['domain'] = url
                # print(d['title'], d['latest'])
                lst.append(d)
                if debug:
                    print(url, d['title'],
                          d['latest'], d['time_updated'])
            except Exception as e:
                print(e, url, update)
        if len(lst) == 0:
            print(f'{self.site} broken check logs')
        return lst

    def __call__(self):
        return self.main()


def test():
    from selenium import webdriver
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.options import Options
    chrome_options = Options()
    chrome_options.add_argument("--window-position=2000,0")
    driver = webdriver.Chrome(
        ChromeDriverManager().install(), options=chrome_options)
    driver.minimize_window()
    driver.get('https://www.google.com/')
    return driver.page_source


if __name__ == "__main__":
    # scans = alphascans , luminousscans, cosmicscans, asurascans
    s = Asura('cosmicscans')
    s.main(debug=True)
