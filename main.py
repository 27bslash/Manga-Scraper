import re
import time
import traceback

from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from db import db
from seleniumbase import BaseCase, SB


class Source:
    def __init__(self, sb: BaseCase) -> None:
        self.sb = sb

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

    def convert_time(self, time_updated: str) -> float:
        # space between dates nov 23 2022 and current date
        if 'today' in time_updated.lower():
            return time.time()
        if 'yesterday' in time_updated.lower():
            return time.time() - 86400
        splt = time_updated.split(" ")
        n = splt[0]
        amount = splt[1].replace("s", "")
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

    def open_the_turnstile_page(self, url):
        self.sb.driver.uc_open_with_reconnect(url, reconnect_time=2)

    def click_turnstile_and_verify(self, success_selector):
        try:
            self.sb.assert_element(success_selector, timeout=1)
        except Exception:
            self.sb.driver.switch_to_frame("iframe")
            self.sb.driver.uc_click("span")
            self.sb.assert_element(success_selector, timeout=1)
        # return self.verify_success()

    def handle_cloudflare(self, url, success_selector):
        # https://github.com/seleniumbase/SeleniumBase/blob/master/examples/raw_turnstile.py
        self.open_the_turnstile_page(url)
        try:
            success = self.click_turnstile_and_verify(success_selector)
            print("successfully passed cloudflare")
            return self.sb.get_page_source()
        except Exception:
            self.open_the_turnstile_page(url)
            success = self.click_turnstile_and_verify(success_selector)
            print("successfully passed cloudflare")
            return self.sb.get_page_source()

    def verify_success(self):
        try:
            self.sb.find_element(
                by="css selector", selector="#challenge-stage", timeout=2
            )
            return False
        except Exception as e:
            return True

    def html_page_source(self, url, success_selector) -> str | None:
        print(url)
        # chrome_options = uc.ChromeOptions()
        # chrome_options.add_argument("--window-position=2000,0")
        # driver = uc.Chrome(use_subprocess=True, options=chrome_options)
        if re.search(r"^[^#|\.]", success_selector):
            # if success selector doesnt start with ". or #"
            return None
        try:
            return self.handle_cloudflare(url, success_selector)
        except Exception as e:
            print(url, e)
            return None
        # try:
        #     print("url get", url)
        #     self.driver.get(url)
        #     # cloudflare test
        #     if self.driver.find_element(By.ID, "challenge-running"):
        #         self.driver.find_element(By.XPATH, "//input[@type='checkbox']").click()
        #         time.sleep(3)
        #     html = self.driver.page_source
        #     return html
        # except Exception as e:

        #     print(
        #         f"page source failed for {url} this should never happen! \n {traceback.format_exc()}"
        #     )
        #     return None

    def __call__(self):
        pass


if __name__ == "__main__":
    strt = time.perf_counter()
    with SB(
        uc_cdp=True,
        guest_mode=True,
        undetectable=True,
    ) as sb:
        src = Source(sb).html_page_source(
            "https://seleniumbase.io/apps/turnstile",
            success_selector="img#captcha-success",
        )
        print(src)
        src = Source(sb).html_page_source(
            "https://reaperscans.com/",
            success_selector=".font-sans",
        )
        print(src)
    pass
