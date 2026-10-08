from config import asura_url
from scrapers.asura import Asura
from scrapers.asuralikes import AsuraLikes
from scrapers.generic import Flame, ManhuaPlus, Scythe, Vortex
from scrapers.hive import Hive
from scrapers.mangadex import MangaDex
from scrapers.reddit import RedditScraper
from scrapers.tcbscans import TcbScraper


def collect_site_scrapes(sb, base_leviatan_url, first_run=False):
    """Run every site scraper and return (sorted entries, offline scraper names)."""
    all_manga = RedditScraper(base_leviatan_url).main(first_run)
    print("combine all manga")

    scrapers = [
        (
            "asurascans",
            lambda: Asura(sb, asura_url, "asurascans").main(include_page_2=first_run),
        ),
        (
            "rizzfables",
            lambda: AsuraLikes(sb, "https://rizzfables.com/", "rizzfables").main(),
        ),
        (
            "hivescans",
            lambda: Hive(sb, "https://hivetoon.com/", "hivescans").scrape(),
        ),
        (
            "tcbscans",
            lambda: TcbScraper(sb).scrape(),
        ),
        (
            "flamescans",
            lambda: Flame(sb).scrape(),
        ),
        (
            "manhua-plus",
            lambda: ManhuaPlus(
                sb, url="https://manhuaplus.com/", scansite="manhua-plus"
            ).scrape(),
        ),
        (
            "scythe",
            lambda: Scythe(sb).scrape(),
        ),
        (
            "vortexscans",
            lambda: Vortex(sb).scrape(),
        ),
        (
            "mangadex",
            lambda: MangaDex().main(),
        ),
    ]

    offline_scrapers = []
    for scraper_name, scraper in scrapers:
        try:
            results = scraper()
            if not results:
                offline_scrapers.append(scraper_name)
                continue
            all_manga.extend(results)
        except Exception:
            offline_scrapers.append(scraper_name)

    filtered = [x for x in all_manga if x.get("time_updated")]
    print(f"{len(filtered)}/{len(all_manga)} entries have time_updated")
    return (
        sorted(filtered, key=lambda k: k["time_updated"], reverse=True),
        offline_scrapers,
    )
