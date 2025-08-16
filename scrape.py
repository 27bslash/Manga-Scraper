import os
import re
import time
import traceback
from pprint import pprint
import json
from pymongo import UpdateOne
import undetected_chromedriver as uc
import pygetwindow as gw
import pyautogui
import requests
from apscheduler.schedulers.background import BlockingScheduler
from thefuzz import fuzz
from seleniumbase import SB, BaseCase
from main import Source
from scrapers.hive import Hive
from scrapers.asura import Asura
from scrapers.asuralikes import AsuraLikes
from scrapers.flame import Flame
from scrapers.leviatan import Leviatan
from scrapers.manhua_updates import ManhuaPlus
from scrapers.reaper import Reaper
from scrapers.reddit import RedditScraper
from scrapers.tcbscans import TcbScraper
from datetime import datetime
from db import db, net_test
from config import (
    testing,
    first_run,
    asura_url,
    leviatan_url,
    luminous_url,
    cosmic_url,
)

from selenium.webdriver import ChromeOptions
from typing import Dict, Optional, TypedDict


class Chapter(TypedDict):
    latest_link: str
    scansite: str


class Sources(TypedDict):
    latest_link: str
    latest: str
    old_chapters: Optional[Dict[str, Chapter]]
    time_updated: float


class ComicData(TypedDict):
    time_updated: float
    title: str
    latest: str
    latest_link: str
    scansite: str
    domain: str
    type: str
    old_chapters: Optional[Dict[str, Chapter]]
    sources: Optional[Dict[str, Sources]]


class Scraper(Source):
    def __init__(self, leviatan, testing):
        self.base_leviatan_url = leviatan
        self.total_manga = []
        self.testing = testing

    def scrape(self, total_manga):
        self.total_manga = total_manga

        curr_urls = db["scans"].find_one({})
        urls = set()

        print(len(total_manga))
        # pprint(total_manga)
        length = len(total_manga)
        scans = self.update_total_manga()
        self.update_users()

        if curr_urls:
            [urls.add(url) for url in curr_urls["urls"]]
        scans = urls.union(scans)
        # pprint(manga_list)
        if not self.testing:
            db["scans"].find_one_and_update(
                {}, {"$set": {"urls": list(urls)}}, upsert=True
            )

    def update_users(self):
        # self.test_search()
        # return
        print("update users")
        for user in db["manga-list"].find({}):
            user_list = user["manga-list"]
            user_id = user["user"]
            if "backup" in user_id:
                continue
            # print('u_id', user_id)
            if user_list:
                self.update_user_list(user_id, user_list)

    def test_search(self):
        for item in self.total_manga:
            for item2 in self.total_manga[::-1]:
                self.fuzzy_search(item["title"], item2["title"])

    def update_user_list(self, user_id, user_list):
        if not self.total_manga:
            with open("new_list.json", "r") as f:
                self.total_manga = json.load(f)
        for total_manga_dict in self.total_manga[::-1]:
            for user_manga in user_list:
                alternate_titles = (
                    set(user_manga['alternate_titles'])
                    if 'alternate_titles' in user_manga
                    else set()
                )
                brk = False
                alternate_titles.add(user_manga['title'])
                for synonym in alternate_titles:
                    search_res = self.fuzzy_search(synonym, total_manga_dict["title"])
                    if search_res > 82:
                        # if 'berserk' in item['title']:
                        #     print('debvug')
                        # sys.stdout.write('\x1b[2K')
                        # if 'novel' in item['title']:
                        #     print('debvug')
                        # print(
                        #     f" \r{length - i}/{length} {item['title']} {item['latest']} {item['scansite']}", end='')
                        user_manga["latest"] = total_manga_dict["sources"]["any"][
                            "latest"
                        ]
                        # if 'world-after' in item['title']:
                        #     print('debug')
                        user_manga["sources"] = self.update_user_sources(
                            user_manga["sources"], total_manga_dict["sources"]
                        )
                        current_source = user_manga["current_source"]
                        curr_source = (
                            "any"
                            if current_source not in user_manga["sources"]
                            else current_source
                        )
                        # print(manga['title'], user_id, manga)
                        user_manga["read"] = float(
                            user_manga["sources"][curr_source]["latest"]
                        ) <= float(user_manga["chapter"])
                        if not user_manga["read"]:
                            print(
                                f"in {user_id} {total_manga_dict['title']} {user_manga['title']} {user_manga['chapter']}/{total_manga_dict['latest']} {total_manga_dict['scansite']} {search_res} 'read: '{user_manga['read']}"
                            )
                            pass
                        brk = True
                        break
                if brk:
                    break
        if not self.testing:
            db["manga-list"].find_one_and_update(
                {"user": user_id}, {"$set": {"manga-list": user_list}}
            )
            pass

    def format_title(self, title):
        t1 = re.sub(r"remake", "", title)
        t1 = re.sub(r"\W+", "", t1)
        return t1

    def update_total_manga(self):
        scans = set()
        all_manga = db["all_manga"].find()

        if not self.total_manga:
            with open("new_list.json", "r") as f:
                self.total_manga = json.load(f)

        bulk_updates = []
        manga_titles = set(item["title"] for item in self.total_manga)
        for i, item in enumerate(self.total_manga[::-1]):
            scans.add(item["domain"])
            item["latest_sort"] = float(item["latest"])

            req = db["all_manga"].find_one({"title": item["title"]})
            print(
                f"\r {len(self.total_manga) - i}/{len(self.total_manga)}", end="\x1b[1K"
            )
            if req and not self.testing:
                bulk_updates.append(UpdateOne({"_id": req["_id"]}, {"$set": item}))
            elif req is None:
                best_match = None
                best_ratio = 0
                for m in all_manga:
                    ratio = fuzz.ratio(item["title"], m["title"])
                    if ratio > 80 and ratio > best_ratio:
                        best_match = m
                        best_ratio = ratio

                if best_match and not self.testing:
                    bulk_updates.append(
                        UpdateOne(
                            {"_id": best_match["_id"]},
                            {"$set": item},
                            upsert=True,
                        )
                    )
                else:
                    bulk_updates.append(
                        UpdateOne({"title": item["title"]}, {"$set": item}, upsert=True)
                    )
        if bulk_updates:
            db["all_manga"].bulk_write(bulk_updates)

        return scans

    def test_total_manga(self):
        with open("new_list.json", "r") as f:
            total_manga = json.load(f)
        for item in total_manga[::-1]:
            item["latest_sort"] = float(item["latest"])
            req = db["all_manga"].find_one({"title": item["title"]})
            updated = False
            if req:
                db["all_manga"].find_one_and_update(
                    {"title": item["title"]}, {"$set": item}
                )
                updated = True
            elif not updated and req is None:
                for m in db["all_manga"].find():
                    ratio = fuzz.ratio(item["title"], m["title"])
                    if ratio > 80:
                        db["all_manga"].find_one_and_update(
                            {"title": m["title"]}, {"$set": item}, upsert=True
                        )
                        updated = True
            if not updated:
                db["all_manga"].find_one_and_update(
                    {"title": item["title"]}, {"$set": item}, upsert=True
                )

    def fuzzy_search(self, title, title2):
        fu = fuzz.ratio(self.format_title(title), self.format_title(title2))
        return fu

    def text_similarity(self, title, title2):
        title_split = title.split("-")
        title_split2 = title2.split("-")
        if title_split == title_split2:
            return True
        ite = title_split
        sub = title_split2
        if len(title_split) < len(title_split2):
            ite = title_split2
            sub = title_split
        ret = len([word for word in ite if word not in sub])
        ret = ret / len(ite)
        return ret <= 0.25

    def update_user_sources(self, user_manga: dict, total_manga: dict) -> dict:
        d = {}
        combined_sources = [total_manga, user_manga]
        for source in total_manga:
            try:
                if source in user_manga:
                    if "url" in user_manga[source]:
                        total_manga[source]["url"] = user_manga[source]["url"]
                    if float(total_manga[source]["latest"]) < float(
                        user_manga[source]["latest"]
                    ):
                        print(
                            f"{total_manga[source]['latest']} < {user_manga[source]['latest']}",
                            user_manga[source]["latest_link"],
                        )
                        # source_list[source]['latest'] = curr[source]['latest']
            except Exception as e:
                print(
                    traceback.format_exc(),
                    total_manga[source]["latest_link"],
                    user_manga[source],
                )
        return total_manga

    def combine_series_by_title(self, lst):
        ret = []
        seen = set()
        # lst = sorted(lst, key=lambda k: k['time_updated'], reverse=True)
        for item in lst:
            title = item["title"]
            if title not in seen:
                ret.append(self.remove_reddit_links(lst, ret, title))
                seen.add(title)
        return ret

    def remove_reddit_links(self, lst, ret, title):
        potential_series = [x for x in lst if self.fuzzy_search(x["title"], title) > 85]
        series = potential_series
        if len(potential_series) > 1:
            highest_chapter = max(
                [x["latest"] if x["type"] == "reddit" else "0" for x in series]
            )
            series = [
                x
                for x in series
                if x["type"] != "reddit"
                and float(x["latest"]) >= float(highest_chapter)
            ]
            if not series:
                series = potential_series
        return series

    def combine_manga_sources(self, source_list):
        sorted_data = sorted(source_list, key=lambda k: k["latest"])
        combined_sources = sorted_data[0]["sources"] | sorted_data[1]["sources"]
        return combined_sources

    def update_manga_sources(self, lst):
        # takes a list of dupes and makes a list of sources
        db_entries = self.atlas_search(lst[0]["title"])
        if len(db_entries) > 1:
            combined_sources = self.combine_manga_sources(db_entries)
            for doc in db_entries:
                doc["sources"] = combined_sources
        # db_entry = db['all_manga'].find_one(
        #     {'title': lst[0]['title']})
        for db_entry in db_entries:
            if "sources" in db_entry and db_entry["sources"]:
                for source_key in db_entry["sources"]:
                    if source_key == "any":
                        continue
                    db_entry["sources"][source_key]["scansite"] = source_key
                    try:
                        updated_source = [
                            source for source in lst if source["scansite"] == source_key
                        ]
                        if updated_source:
                            db_entry["sources"][source_key] = updated_source[0]
                            db_entry["sources"][source_key]["latest_link"] = (
                                updated_source[0]["latest_link"]
                            )
                            db_entry["sources"][source_key]["time_updated"] = (
                                updated_source[0]["time_updated"]
                            )
                            if "old_chapters" in updated_source[0]:
                                db_entry["sources"][source_key]["old_chapters"] = (
                                    updated_source[0]["old_chapters"]
                                )
                        lst.append(db_entry["sources"][source_key])
                    except Exception as e:
                        print(lst, traceback.format_exc())
            try:
                latest_sort = sorted(
                    lst,
                    key=lambda k: (float(k["latest"]), -k["time_updated"]),
                    reverse=True,
                )
                # print(latest_sort)
                updated_sources = {}
                # pprint(latest_sort)
                # print('latest', latest_sort[0])
                old_chapters = {}
                if "old_chapters" in latest_sort[0]:
                    old_chapters = latest_sort[0]["old_chapters"]
                source_string = {
                    "latest": latest_sort[0]["latest"],
                    "latest_link": latest_sort[0]["latest_link"],
                    "time_updated": latest_sort[0]["time_updated"],
                    "old_chapters": old_chapters,
                }
                updated_sources["any"] = source_string

                for item in latest_sort[::-1]:
                    old_chapters = {}
                    if "old_chapters" in item:
                        old_chapters = item["old_chapters"]
                    source_string = {
                        "latest": item["latest"],
                        "latest_link": item["latest_link"],
                        "time_updated": item["time_updated"],
                        "old_chapters": old_chapters,
                    }
                    try:
                        # pprint(item)
                        updated_sources[item["scansite"]] = source_string
                    except KeyError:
                        print("e", item)
                return updated_sources
            except Exception as e:
                print(traceback.format_exc())

    def atlas_search(self, title):
        search_query = {
            "$search": {
                "index": "default",
                "text": {
                    "query": title,
                    "path": "title",
                    # 'fuzzy': {
                    #     'maxEdits': 2,
                    #     'maxExpansions': 100
                    # }
                },
            }
        }
        query = [
            search_query,
            {"$limit": 3},
            {
                "$project": {
                    "score": {"$meta": "searchScore"},
                    "_id": 0,
                    "title": 1,
                    "latest": 1,
                    "sources": 1,
                    "latest_sort": 1,
                    "scansite": 1,
                }
            },
        ]
        res = db["all_manga"].aggregate(query)
        fuzzysearch = list(res)
        fuzzysearch = [
            doc
            for doc in fuzzysearch
            if doc["score"] >= fuzzysearch[0]["score"] * 0.7
            and abs(float(doc["latest"]) - float(fuzzysearch[0]["latest"])) < 5
        ]
        return fuzzysearch

    def combine_data(self, sb, first_run=False):
        total_manga = RedditScraper(self.base_leviatan_url).main(first_run)
        all_manga = total_manga
        print("combine all manga")
        asura2 = []
        asura = Asura(sb, asura_url, "asurascans").main()
        if asura and first_run:
            asura2 = Asura(sb, f"{asura_url}/page/2/", "asurascans").main()
        # alpha = Asura('https://alpha-scans.org/', 'alphascans').main()
        # cosmic = Asura(sb, cosmic_url, "cosmicscans").main()
        luminous = AsuraLikes(sb, luminous_url, "luminouscans").main()
        riz_comics = AsuraLikes(sb, "https://rizzfables.com/", "rizzfables").main()
        hive_scans = Hive(sb, 'https://hivetoon.com/', 'hivescans').scrape()
        # void = Asura(sb, void_url, "voidscans").main()
        # leviatan = Leviatan(sb, 'https://lscomic.com/', 'leviatanscans').scrape()
        # reaper = Reaper(sb).scrape()
        tcb = TcbScraper(sb).scrape()
        flame = Flame(sb).scrape()
        # flix = Flix(sb).scrape()
        manhua_plus = ManhuaPlus(
            sb, url='https://manhuaplus.com/', scansite="manhua-plus"
        ).scrape()
        manhua_fast = ManhuaPlus(
            sb, url='https://manhuafast.net/', scansite="manhuafast"
        ).scrape()

        all_manga += (
            asura
            + asura2
            + luminous
            + riz_comics
            + hive_scans
            # + void
            # + leviatan
            # + reaper
            + tcb
            + flame
            # + flix
            + manhua_plus
            + manhua_fast
        )

        # all_manga += leviatan
        # all_manga = tcb

        # pprint(all_manga)
        all_manga = sorted(all_manga, key=lambda k: k["time_updated"], reverse=True)

        return all_manga

    @staticmethod
    def api_test():
        req = requests.get("https://27bslash.eu.pythonanywhere.com/heart_beat")
        return req.status_code

    def main(self, first_run=False):
        os.system("cls")
        if not net_test(500):
            return
        print("flask api test results: ", self.api_test())
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
            total_manga: list[list[ComicData]] = self.combine_series_by_title(
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
                d["sources"] = self.update_manga_sources(manga)
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
        self.scrape(new_list)
        print("\ntime taken", time.perf_counter() - srt)
        return new_list


def get_leviatan_url():
    req = requests.get("https://lscomic.com//")
    return req.url


def change_leviatan_url(base_url):
    # base_url = 'https://lscomic.com//omg'
    lst = db["manga-list"].find({})
    regex = r".*leviatan.*(?=\/manga)"
    for entry in lst:
        user = entry["user"]
        manga_list = entry["manga-list"]
        for doc in manga_list:
            if "link" in doc:
                doc["link"] = re.sub(regex, base_url, doc["link"])
            for source in doc["sources"]:
                if "link" in source:
                    source["link"] = re.sub(regex, base_url, source["link"])
                if "latest_link" in source:
                    source["latest_link"] = re.sub(
                        regex, base_url, source["latest_link"]
                    )
                if "url" in source:
                    source["url"] = re.sub(regex, base_url, source["url"])
        db["manga-list"].find_one_and_update(
            {"user": user}, {"$set": {"manga-list": manga_list}}
        )


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
    # Scraper(leviatan_url).update_total_manga()
    # Scraper(leviatan_url).main(first_run=first_run)
    # with open("total_manga.json", "r") as f:
    #     data = json.load(f)
    #     Scraper("False", False).combine_series_by_title(data)
    # time.sleep(10000)

    time.sleep(60)
    cleanup_mei()
    while True:
        try:
            if net_test():
                if first_run and not testing:
                    leviatan_url = get_leviatan_url()
                    change_leviatan_url(base_url=leviatan_url)
                scraper = Scraper(leviatan_url, testing)
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
                    pass
                except Exception as e:
                    print(e, e.__class__)
                    scheduler.shutdown()
        except Exception:
            print(traceback.format_exc())
            time.sleep(300)
