import re
import time
import traceback

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from db import db
import undetected_chromedriver as uc


class Source:
    def __init__(self, driver) -> None:
        self.driver = driver

    def update_manga_dict(self, manga, item):
        if item["latest"] > manga["chapter"]:
            manga["read"] = False
            # this will run every time make it update only once
            manga["latest"] = item["latest"]
            if "link" not in manga:
                manga["link"] = item["link"]
            manga["domain"] = item["domain"]
            manga["test"] = True
        else:
            manga["read"] = True
        return manga

    def update_sources(self, curr, scansite, item):
        db_entry = db["all_manga"].find_one({"title": item["title"]})
        # if 'sss' in item['title']:
        # print(scansite, db_entry['sources'])
        source_string = {
            "url": curr["link"],
            "latest": item["latest"],
            "latest_link": item["link"],
            "time_updated": item["time_updated"],
        }
        if not db_entry:
            db_entry = {"sources": {}}
        if "sources" not in db_entry:
            db_entry["sources"] = {}
        if "any" not in db_entry["sources"]:
            db_entry["sources"]["any"] = source_string
        if db_entry["sources"]["any"]["latest"] < item["latest"]:
            db_entry["sources"]["any"] = source_string
        elif db_entry["sources"]["any"]["time_updated"] >= item["time_updated"]:
            #     print('any')
            # print(item['title'])
            # print(db_entry['sources'])
            db_entry["sources"]["any"] = source_string
        # print(db_entry['sources']['any']['time_updated'], item['time_updated'], db_entry['sources']
        #       ['any']['latest'], item['latest'], db_entry['sources']['any']['time_updated'] < item['time_updated'])
        db_entry["sources"][scansite] = source_string
        return db_entry["sources"]

    def clean_title(self, title):
        return (
            re.sub(r"\s\s+", " ", title)
            .strip()
            .replace(" ", "-")
            .replace("\n", "")
            .lower()
        )

    def clean_chapter(self, chapter):
        regex = r"(?<=Chapter )\d+"
        match = re.search(regex, chapter)
        if match:
            return match.group().strip()
        else:
            return re.sub(r"[^\d\.]+", "", chapter.replace("Chapter ", "").strip())

    def convert_time(self, time_updated):
        # space between dates nov 23 2022 and current date
        time_updated = time_updated.split(" ")
        n = time_updated[0]
        amount = time_updated[1].replace("s", "")
        current_time = time.time()
        if amount == "second":
            current_time -= int(n)
        elif amount == "minute":
            current_time -= int(n) * 60
        elif amount == "hour":
            current_time -= int(n) * 60 * 60
        elif amount == "day":
            current_time -= int(n) * 60 * 60 * 24
        elif amount == "week":
            current_time -= int(n) * 60 * 60 * 24 * 7
        elif amount == "month":
            current_time -= int(n) * 60 * 60 * 24 * 30
        elif amount == "year":
            current_time -= int(n) * 60 * 60 * 24 * 30 * 12
        return current_time

    def main(self):
        # self.scrape(first_run=True)
        pass

    def html_page_source(self, url) -> str | None:
        print(url)
        # chrome_options = uc.ChromeOptions()
        # chrome_options.add_argument("--window-position=2000,0")
        # driver = uc.Chrome(use_subprocess=True, options=chrome_options)
        try:
            print("url get", url)
            self.driver.get(url)
            html = self.driver.page_source
            return html
        except Exception as e:
            print(traceback.format_exc())
            return None

    def __call__(self):
        self.main()
        pass


if __name__ == "__main__":
    strt = time.perf_counter()
    Source('').html_page_source("https://www.google.com")
    print(time.perf_counter() - strt)
    pass
