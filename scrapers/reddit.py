import praw
import re
from pprint import pprint
import pymongo
import os
import time
from dotenv import load_dotenv
import requests
from config import asura_url, flame_url, cosmic_url, luminous_url, base_reaper_url

load_dotenv()
connection = os.environ["DB_CONNECTION"]
cluster = pymongo.MongoClient(f"{connection}?retryWrites=true&w=majority")
db = cluster["manga-scraper"]


class RedditScraper:
    def __init__(self, leviatan) -> None:
        self.base_leviatan_url = leviatan
        self.banned_domains = [
            "alpha scans",
            "leviatan scans",
            "reaper scans",
            "luminous scans",
            "flame scans",
            "asura scans",
        ]

    def get_url(self, submission, title, chapter_num):
        if submission.selftext:
            if "http" in submission.selftext:
                # print('self text', submission.selftext)
                return self.get_domain_from_self_post(submission, title, chapter_num)
            else:
                return self.get_banned_domains(submission, title, chapter_num)
        elif "reddit" in submission.url or "cubari" in submission.url:
            return self.get_banned_domains(submission, title, chapter_num)
        else:
            return submission.url

    def get_domain_from_self_post(self, submission, title, chapter_num):
        self_text_html = submission.selftext_html
        link_regex = r"(?<=href=\").*?(?=\")"
        links = re.findall(link_regex, self_text_html)
        lnk = [
            lnk
            for lnk in links
            if "cubari" not in lnk and "discord" not in lnk and "mail" not in lnk
        ]
        mirror = [
            lnk
            for lnk in links
            if "cubari" in lnk and "discord" not in lnk and "mail" not in lnk
        ]
        # print(title, 'lnk', lnk)
        if links is None:
            return self.banned_urls(submission.selftext.lower(), title, chapter_num)
        elif mirror:
            if self.banned_urls(submission.title.lower(), title, chapter_num):
                return self.banned_urls(submission.title.lower(), title, chapter_num)
            else:
                print("mirror", title, mirror[0])
                return mirror[0]
        elif len(lnk) == 1:
            # print('lnk 1', title, chapter_num, lnk[0])
            return lnk[0]
        elif len(lnk) > 1:
            # print('lnk 2', title, chapter_num, lnk[len(lnk)-1])
            return lnk[len(lnk) - 1]
        else:
            print("else", title, chapter_num, lnk)
            return self.banned_urls(submission.selftext.lower(), title, chapter_num)

    def get_banned_domains(self, submission, title, chapter_num):
        for name in self.banned_domains:
            if name in submission.title.lower() or name in submission.selftext.lower():
                title = title.replace(" ", "-")
                return self.banned_urls(name, title, chapter_num)
        # print(title, submission.url)
        return submission.url

    def banned_urls(self, name, title, chapter_num):
        title = title.replace("'", "")
        title = re.sub(r"–", "-", title)
        title = re.sub(r"-+", "-", title)
        url = None
        if "reaper" in name:
            url = f"{base_reaper_url}series/{title}/chapter-{chapter_num}/"
        elif "leviatan" in name:
            url = f"{self.base_leviatan_url}/manga/{title}/chapter-{chapter_num}/"
        elif "luminous" in name:
            url = f"{luminous_url}{title}-chapter-{chapter_num}/"
        elif "alpha" in name:
            url = f"https://alpha-scans.org/{title}-chapter-{chapter_num}"
        elif "flame" in name:
            url = f"{flame_url}{title}-chapter-{chapter_num}"
        elif "asura" in name:
            url = f"{asura_url}{title}-chapter-{chapter_num}/"
        elif "cosmic" in name:
            url = f"{cosmic_url}{title}-chapter-{chapter_num}/"
        return url

    def get_title(self, submission, testing=False):
        title_regex = r".*?(?= \(?ch |ch\.|ep |chapter|season|episode|::|vol\.)"
        if testing:
            base_title_string = submission
        else:
            base_title_string = submission.title
        title = re.findall(title_regex, base_title_string, re.IGNORECASE)
        flag = False
        if not title:
            title = re.findall(
                r".*?(?= \(?ch |ch\.|ep |chapter|season|episode|::|vol\.|\d|s\d+)",
                base_title_string,
                re.IGNORECASE,
            )

            flag = True
        if title:
            title = re.sub(r"\s?\-\s?$", "", title[0])
            if "webtoons" in submission.url:
                title = re.sub(r"Season.*", "", title)
            title = re.sub(r"\[.*DISC.*\]", "", title, flags=re.IGNORECASE)
            title = re.sub(r"::", "", title)
            title = re.sub(r"[|()\[\]]", "", title)
            title = title.replace("&", "and")
            title = title.strip().lower()
            title = re.sub(r"\W$", " ", title)
            title = title.strip()
            title = title.replace(" ", "-").replace("’", "'")
            title = title.replace("---", "-")

            # if flag:
            #     print('new title', title)
            return title
        else:
            return None

    def get_scans(self, title=None, url=None):
        # scan_regex = "[a-z-]*(?=\.)"
        if title:
            title = re.sub(r"\[.*DISC.*\]", "", title, flags=re.IGNORECASE)
            # extract scans from [] () or after | symbol
            scan_regex = r"\[.*\]|\(.*\)|(?=\|).*|"
            scan_site = re.findall(scan_regex, title, re.IGNORECASE)
            scan_site = [str for str in scan_site if len(str) > 0]
            if len(scan_site) > 0 and "cubari" not in title.lower():
                scan_site = (
                    re.sub(r"[\]\[\(\)\|\s]", "", scan_site[len(scan_site) - 1])
                    .strip()
                    .lower()
                )
                if (
                    "revised" in scan_site
                    or "draw" in scan_site
                    or "volume" in scan_site
                ):
                    return None
                return scan_site.replace("-", "")
            return None
        url = re.sub(r"viewer|reader", "", url)
        if url:
            scan_regex = r"\w+-?\w+(?<!www)(?=\.)"
            try:
                scan_site = re.findall(scan_regex, url, re.IGNORECASE)[0]
                return scan_site.replace("-", "")
            except Exception as e:
                return

    def get_banned_domain(self, scan_site):
        if scan_site == "alpha":
            return "alpha-scans.org"
        elif scan_site == "leviatan":
            return "leviatan-scans.com"
        elif scan_site == "reaper":
            return "reaperscans.com"
        elif scan_site == "luminous":
            return "luminousscans.com"
        elif scan_site == "flame":
            return "flamescans.org"
        return

    def get_todays_list(self, first_run=False):
        """
        reads praw.ini file or .env file
        required fields
        client_id
        client_secret
        user_agent
        """

        # reddit = praw.Reddit('MANGA')
        reddit = praw.Reddit(
            check_for_updates=True,
            comment_kind="t1",
            message_kind="t4",
            redditor_kind="t2",
            submission_kind="t3",
            subreddit_kind="t5",
            trophy_kind="t6",
            oauth_url="https://oauth.reddit.com",
            ratelimit_seconds=5,
            reddit_url="https://www.reddit.com",
            short_url="https://redd.it",
            timeout=16,
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
            user_agent=os.environ["USER_AGENT"],
        )
        manga_list = []
        submissions = []
        limit = 50
        sort = "new"
        if first_run:
            limit = None
            sort = "hot"

        for submission in reddit.subreddit("manga").search(
            'flair:"DISC"', sort=sort, limit=limit
        ):
            submissions.append(submission)
        for submission in reddit.subreddit("manga").search("*", limit=limit, sort=sort):
            if "disc" in submission.title.lower():
                if submission not in submissions:
                    submissions.append(submission)
        for submission in submissions[::-1]:
            # print(submission.title)
            d = {}
            scan_site = None
            title = None
            chapter_num = None
            url = None
            domain = None
            if re.search(r"\braws?\b|\[raws?\]", submission.title.lower()):
                continue
            if "@" in submission.title:
                # twitter manga filter
                continue
            title = self.get_title(submission)
            if not title:
                print(f"{submission.title} has no title")
                continue
            chapter_num = self.get_chapter_number(submission)
            if not chapter_num:
                continue
            if "one punch" in submission.title.lower():
                pass
            # scan_site = self.get_scans(title=submission.title)
            url = self.get_url(
                submission=submission, title=title, chapter_num=chapter_num
            )
            # print(title, chapter_num)
            domain = submission.domain
            if "self.manga" in domain:
                domain = self.extract_domain(url)
                if submission.selftext:
                    for name in self.banned_domains:
                        if name in submission.selftext.lower():
                            scan_site = name.replace(" ", "")
                            break

                if scan_site is None and url is not None:
                    sc_site = self.get_scans(title=submission.title)
                    if sc_site:
                        if re.search(r"\d+", sc_site):
                            sc_site = self.get_scans(url=url)
                    else:
                        sc_site = self.get_scans(url=url)
                    scan_site = sc_site
            elif "i.redd" in domain:
                continue
            elif "cubari" in domain:
                # print(submission.title, domain)
                scan_site = self.get_scans(title=submission.title)
                if url:
                    domain = self.extract_domain(url)
                    # print('domain2', domain)
                if "cubari" in domain or scan_site is None:
                    db_entry = db["all_manga"].find_one({"title": title})
                    banned_flag = False
                    if db_entry and float(chapter_num) - float(db_entry["latest"]) < 3:
                        domain = db_entry["domain"]
                        scan_site = self.get_scans(url=domain)
                        for banned_domain in self.banned_domains:
                            if banned_domain in db_entry["domain"]:
                                scan_site = banned_domain.replace(" ", "")
                                url = self.banned_urls(
                                    banned_domain, title, chapter_num
                                )
                                if banned_domain != "flame":
                                    banned_flag = True
                                break
                    else:
                        print("cubariu", title)
                        scan_site = "cubari"
                        url = submission.url
                        domain = "https://cubari.moe/"
                    if banned_flag:
                        continue
            elif "reddit.com" in domain:
                # print('reddit', title)
                url = submission.url
                # print(vars(submission))
                # weird self post comment redirect'
                if "comments" in submission.url:
                    search = re.search(r"(?<=comments/)\w+", url, re.IGNORECASE)
                    subm = reddit.submission(id=search.group(0))
                    try:
                        domain = subm.domain
                        if domain and "reddit" not in domain:
                            url = self.get_url(subm, title, chapter_num)
                    except Exception as e:
                        print("submission error", e, title, chapter_num)
                domain = self.extract_domain(url)
                if (
                    domain
                    and "reddit" not in domain
                    and "twitter" not in domain
                    and "cubari" not in domain
                ):
                    scan_site = self.get_scans(url=domain)
                else:
                    # print(title, 'no domain', chapter_num)
                    continue
            else:
                url = submission.url
                scan_site = self.get_scans(url=domain)
                # print(title, domain, scan_site)
            if not url or "reddit" in url:
                print("no url", title, chapter_num, domain, submission.url)
                continue
            if not scan_site:
                print("no scan site", title, chapter_num, domain, submission.url)
                continue
            if "ch" in scan_site:
                # print('ch', title, scan_site)
                continue
            if "reddit" in scan_site:
                continue
            if "flame" in scan_site and "extra" in title:
                continue
            d["type"] = "reddit"
            d["time_updated"] = submission.created_utc
            d["title"] = title
            d["latest"] = chapter_num
            d["domain"] = domain
            d["latest_link"] = url
            d["scansite"] = scan_site
            # print(d['title'], d['latest'], d['latest_link'])
            # d['sources'] = super().update_sources(d, scan_site, d)
            # print(d['title'], d['latest'])
            manga_list.append(d)
        return manga_list

    def extract_domain(self, url):
        if not url:
            return
        regex = r"^(?:https?:\/\/)?(?:[^@\/\n]+@)?(?:www\.)?([^:\/?\n]+)"
        try:
            return re.search(regex, url).group()
        except Exception as e:
            print(url, e, e.__class__)

    def get_chapter_number(self, submission):
        title = submission.title
        if "webtoons" in submission.url:
            match = re.search(r"(?<=episode_no=).*", submission.url)
            if match:
                return match.group()
        chapter_num = self.get_chapter_num_from_title(title)
        return chapter_num

    def get_chapter_num_from_title(self, title: str):
        # chapter_regex = r".*(?<=chapter|episode)|.*(?<=ch|ep)"
        # chapter_regex = r"(?<=Ch\.|Episode|Chapter)\s?(\d+\.?\-?\d+)"
        chapter_regex = R"(?<=Episode|Chapter)\:*\-?\s?(\d+\.?\-?\d+)|(?<=Ep|Ch)\.?\s?(\d+\.?\-?\d+)"
        matches = re.findall(chapter_regex, title, re.IGNORECASE)
        # print(matches)
        pot_chapters = []
        if matches:
            for match in matches:
                for group in match:
                    pot_chapters.append(max(group.split("-")))
            chapter_num = max(pot_chapters)
            chapter_num = re.sub(r"^0+", "", chapter_num)
            chapter_num = re.sub(r"^\W+", "", chapter_num)
            return chapter_num

            # pot_chapters = re.findall(r"(?<=[\W])\d*\.?\d+", match)
            # pot_chapters = sorted(pot_chapters, key=float, reverse=True)
            # if not pot_chapters:
            #     return None
            # chapter_num = pot_chapters[0]
            # chapter_num = re.sub(r"^0+", '', chapter_num)
            # chapter_num = re.sub(r"^\W+", '', chapter_num)
            # if 'Spoiler' in chapter_num:
            #     print(title)
            # return chapter_num
        # matches = re.findall(r"\d+\.?\d*", title)
        # if matches:
        #     match = matches[len(matches)-1]
        #     res = re.sub(r"^0+", '', match)
        #     return res

    def main(self, first_run=False):
        return self.get_todays_list(first_run)


if __name__ == "__main__":
    RedditScraper("https://lscomic.com/").main(False)
