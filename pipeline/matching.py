import re

from thefuzz import fuzz


def format_title(title):
    t1 = re.sub(r"remake", "", title)
    t1 = re.sub(r"\W+", "", t1)
    return t1


def fuzzy_search(title, title2):
    fu = fuzz.ratio(format_title(title), format_title(title2))
    return fu


def text_similarity(title, title2):
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


class SeriesCombiner:
    """Groups scraped entries into series and drops low-value reddit rows."""

    def __init__(self, fuzzy_search_fn=None):
        self.fuzzy_search = fuzzy_search_fn or fuzzy_search

    def combine(self, lst):
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
