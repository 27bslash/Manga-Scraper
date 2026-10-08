import json
import os
import time
import traceback
from datetime import datetime

import pyautogui
from apscheduler.schedulers.background import BlockingScheduler
from selenium.webdriver import ChromeOptions
from seleniumbase import SB

from config import (
    first_run,
    leviatan_url,
)
from db import db, net_test
from main import Source
from pipeline.matching import SeriesCombiner, fuzzy_search, text_similarity
from pipeline.models import ComicData
from pipeline.site_scrapers import collect_site_scrapes
from pipeline.sources import SourceMerger
from pipeline.titles import TITLE_QUALIFIER_TOKENS
from pipeline.total_sync import TotalMangaScraper
from pipeline.user_sync import UserMangaScraper
from ws_publish import broadcast_event, build_update_payload


class Scraper(Source):
    def __init__(self, leviatan, testing):
        self.base_leviatan_url = leviatan
        self.total_manga = []
        self.testing = testing
        self.offline_scrapers = []
        self.series_combiner = SeriesCombiner(fuzzy_search_fn=fuzzy_search)
        self.source_merger = SourceMerger()

    def scrape(self, total_manga):
        self.total_manga = total_manga
        user_scraper = UserMangaScraper(
            total_manga=self.total_manga,
            testing=self.testing,
            fuzzy_search=fuzzy_search,
            qualifier_tokens=TITLE_QUALIFIER_TOKENS,
        )
        total_manga_scraper = TotalMangaScraper(
            total_manga=self.total_manga,
            testing=self.testing,
            text_similarity_fn=text_similarity,
        )

        curr_urls = db["scans"].find_one({})
        urls = set()

        print(len(total_manga))
        # pprint(total_manga)
        length = len(total_manga)
        scans = total_manga_scraper.update_total_manga()
        changed_users = user_scraper.update_users()

        if curr_urls:
            [urls.add(url) for url in curr_urls["urls"]]
        scans = urls.union(scans)
        # pprint(manga_list)
        if not self.testing:
            db["scans"].find_one_and_update(
                {}, {"$set": {"urls": list(urls)}}, upsert=True
            )
        return changed_users

    def combine_data(self, sb, first_run=False):
        total_manga, offline_scrapers = collect_site_scrapes(
            sb, self.base_leviatan_url, first_run
        )
        self.offline_scrapers = offline_scrapers
        return total_manga

    def main(self, first_run=False):
        os.system("cls")
        self.offline_scrapers = []
        if not net_test(500):
            return
        if self.testing:
            with open(
                "pre_processed.json",
                "r",
            ) as f:
                data = json.load(f)
        else:
            chrome_options = ChromeOptions()
            if should_switch_window():
                chrome_options.add_argument("--window-position=2000,0")
            try:
                with SB(
                    uc_cdp=True,
                    guest_mode=True,
                    undetectable=True,
                    headless2=True,
                ) as sb:
                    total_manga = self.combine_data(sb, first_run)
            except Exception:
                print("selenium failed to start")
                sb.driver.quit()
                return
            # with open("D:\\projects\\python\\reddit-manga\\total_manga.json", "w") as f:
            #     json.dump(total_manga, f, indent=4)
            total_manga: list[list[ComicData]] = self.series_combiner.combine(
                total_manga
            )
            data = total_manga
            # with open(
            #     "D:\\projects\\python\\reddit-manga\\pre_processed.json", "w"
            # ) as f:
            #     json.dump(data, f, indent=4)
            print(len(total_manga))
        srt = time.perf_counter()
        new_list = []

        for manga in data:
            try:
                d = {}
                d = manga[0]
                # print(d['title'])
                d["sources"] = self.source_merger.update_manga_sources(manga)
                if "old_chapters" in d:
                    del d["old_chapters"]
                new_list.append(d)
            except Exception:
                print(traceback.format_exc())
                with open("err.txt", "w") as f:
                    f.write(str(datetime.now()))
                    f.write(traceback.format_exc())
                    f.write(str(manga))
        with open("D:\\projects\\python\\reddit-manga\\new_list.json", "w") as f:
            json.dump(new_list, f, indent=4)
        changed_users = self.scrape(new_list)
        if changed_users:
            try:
                sent = broadcast_event(
                    build_update_payload(),
                    user_ids=changed_users,
                )
                print(
                    f"WebSocket notify sent to {sent} connections "
                    f"for {len(changed_users)} changed users"
                )
            except Exception:
                print("WebSocket notify failed")
                print(traceback.format_exc())
        else:
            print("WebSocket notify skipped: no user manga-list changes")
        print("\ntime taken", time.perf_counter() - srt)
        report_width = max(
            42,
            max((len(name) for name in self.offline_scrapers), default=0) + 12,
        )
        print("\n" + "=" * report_width)
        print("SCRAPER STATUS".center(report_width))
        print("-" * report_width)
        if self.offline_scrapers:
            print(f" {len(self.offline_scrapers)} scraper(s) offline:")
            for scraper_name in self.offline_scrapers:
                print(f"  [DOWN] {scraper_name}")
        else:
            print("  [OK] All scrapers returned data")
        print("=" * report_width)
        return new_list


def should_switch_window() -> bool:
    x, y = pyautogui.position()
    return x < 1920


def cleanup_mei():
    """
    Rudimentary workaround for https://github.com/pyinstaller/pyinstaller/issues/2379
    """
    import sys
    import os
    from shutil import rmtree

    mei_bundle = getattr(sys, "_MEIPASS", False)
    print("cleaning MEI files")
    if mei_bundle:
        print("mei_bundle found")

        dir_mei, current_mei = mei_bundle.split("_MEI")
        for file in os.listdir(dir_mei):
            if file.startswith("_MEI") and not file.endswith(current_mei):
                try:
                    print('remove mei', file)
                    rmtree(os.path.join(dir_mei, file))
                except (
                    PermissionError
                ):  # mainly to allow simultaneous pyinstaller instances
                    pass


# scrape(None, False)
if __name__ == "__main__":
    # Scraper(leviatan_url, testing=False).update_total_manga()
    # Scraper(leviatan_url, testing=False).main(first_run=first_run)
    # with open("total_manga.json", "r") as f:
    #     data = json.load(f)
    #     SeriesCombiner().combine(data)
    # time.sleep(10000)
    cleanup_mei()
    while True:
        try:
            if net_test():
                scraper = Scraper(leviatan_url, testing=False)
                scraper.main(first_run=first_run)
                time.sleep(1800)
                scheduler = BlockingScheduler()
                try:
                    scheduler.add_job(
                        scraper.main,
                        "cron",
                        timezone="Europe/London",
                        start_date=datetime.now(),
                        id="scrape",
                        hour="*",
                        minute="*/30",
                        day_of_week="mon-sun",
                    )
                    scheduler.start()

                except Exception as e:
                    print(e, e.__class__)
                    scheduler.shutdown()
        except Exception:
            print(traceback.format_exc())
            time.sleep(300)
