import datetime
from pprint import pprint
import re
import traceback
import requests
from bs4 import BeautifulSoup
from main import Source

from config import leviatan_url


class Leviatan(Source):
    def main(self):
        req = requests.get(leviatan_url)
        print(req.status_code)
        # with open('scrapers/test_pages/leviatan.html', 'w', encoding="utf-8") as f:
        #     f.write(req.text)
        # pass

    def convert_dates(self, date):
        try:
            date_object = datetime.datetime.strptime(date.strip(), "%b %d, %Y")
            stamp = date_object.timestamp()
            return stamp
        except:
            return None

    def scrape(self, debug=False):
        # self.main()
        # with open('scrapers/test_pages/leviatan.html', 'r', encoding="utf-8") as f:
        #     text = f.read()
        print("scraping leviatan")
        lst = []
        title_list = []
        try:
            req = requests.get(leviatan_url)
        except:
            return []
        if req.status_code != 200:
            print("leviatan", req.status_code, "broken")
            text = super().html_page_source(leviatan_url)
            if not text:
                return []
        else:
            text = req.text

        # with open('scrapers/test_pages/leviatan.html', 'w', encoding="utf-8") as f:
        #     f.write(text)
        # with open('scrapers/test_pages/leviatan.html', 'r', encoding="utf-8") as f:
        #     text = f.read()

        soup = BeautifulSoup(text, "html.parser")
        chapters = soup.select('div[class*="chapter-item"]')
        titles = soup.select('div[class*="post-title"]')
        item_summary = soup.select('div[class*="item-summary"]')
        for item in item_summary:
            d = {}
            title_el = item.find("div", "post-title").find("a").text
            title = super().clean_title(title_el)
            try:
                chapter_el = item.find("div", "chapter-item")
                if not chapter_el:
                    continue
                chapter = super().clean_chapter(chapter_el.find("span").text)
                link_el = chapter_el.find("a").get("href")
                a_tags = chapter_el.find_all("a")
                time_el = None
                for tag in a_tags:
                    if tag.has_attr("title"):
                        time_el = tag.attrs["title"]
                        break
                if time_el is None:
                    o = chapter_el.find_all("span")
                    time_el = o[-1].text
                time_updated = self.convert_dates(time_el)
                if not time_updated:
                    time_updated = super().convert_time(time_el)
                if not title or not chapter or not link_el:
                    continue

                d["type"] = "leviatan"
                d["title"] = title
                d["latest"] = re.search(r"\d+", chapter).group(0)
                d["latest_link"] = link_el
                d["time_updated"] = time_updated
                d["scansite"] = "leviatanscans"
                d["domain"] = "https://lscomic.com/"
                lst.append(d)
                if debug:
                    print("leviatan", title, chapter, time_updated)
            except Exception as e:
                print("leviatan", title, traceback.format_exc())
                pass
        if len(lst) == 0:
            print("leviatan broken check logs")
        return lst
        # print(lst)
        # for card in titles:
        #     link = card.find_all('a')
        #     print(link)
        # chapter =


if __name__ == "__main__":
    s = Leviatan().scrape(True)
