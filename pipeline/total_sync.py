import json

from pymongo import UpdateOne
from thefuzz import fuzz

from db import db
from pipeline.titles import FUZZY_IDENTITY_THRESHOLD, PrefixCandidateIndex


class TotalMangaScraper:
    def __init__(
        self,
        total_manga,
        testing,
        text_similarity_fn=None,
        fuzzy_identity_threshold=FUZZY_IDENTITY_THRESHOLD,
        prefix_len: int = 2,
        max_prefix_len: int = 5,
        target_bucket_size: int = 30,
    ):
        self.total_manga = total_manga
        self.testing = testing
        self.text_similarity_fn = text_similarity_fn or (lambda _a, _b: True)
        self.fuzzy_identity_threshold = fuzzy_identity_threshold
        self.prefix_len = prefix_len
        self.max_prefix_len = max_prefix_len
        self.target_bucket_size = target_bucket_size
        self.index = PrefixCandidateIndex(
            prefix_len=prefix_len,
            max_prefix_len=max_prefix_len,
            target_bucket_size=target_bucket_size,
        )

    def _ensure_sorted_all_manga_titles(self, all_manga_titles: list[dict]):
        self.index.ensure_sorted(all_manga_titles)

    def _exact_match_for_item(self, item, candidates):
        return [
            manga_title
            for manga_title in candidates
            if manga_title['title'] == item['title']
        ]

    def _best_fuzzy_match(self, item, candidates, _id_set):
        best_match = None
        best_ratio = 0
        for manga in candidates:
            ratio = fuzz.ratio(item["title"], manga["title"])
            if ratio < self.fuzzy_identity_threshold or ratio <= item.get(
                'best_score', 0
            ):
                continue
            if not self.text_similarity_fn(item["title"], manga["title"]):
                continue
            if manga['_id'] in _id_set:
                continue
            if ratio > best_ratio:
                best_match = manga
                best_ratio = ratio
        return best_match, best_ratio

    def update_total_manga(self):
        scans = set()
        all_manga = db["all_manga"].find({}, projection={'_id': 1, 'title': 1})

        if not self.total_manga:
            with open("new_list.json", "r") as f:
                self.total_manga = json.load(f)
        all_manga_titles = [
            {
                "title": manga['title'],
                "_id": manga['_id'],
                "best_score": manga.get('best_score') or 0,
                "closest_title": manga.get('closest_title'),
            }
            for manga in all_manga
        ]
        self.index.reset(all_manga_titles)
        bulk_updates = []
        _id_set = set()

        for i, item in enumerate(self.total_manga[::-1]):
            scans.add(item["domain"])
            item["latest_sort"] = float(item["latest"])

            candidates = self.index.candidates(item["title"], all_manga_titles)
            exact_match = self._exact_match_for_item(item, candidates)
            print(
                f"\r {len(self.total_manga) - i}/{len(self.total_manga)}", end="\x1b[1K"
            )

            if exact_match:
                if exact_match[0]["_id"] in _id_set:
                    print(f"skipping {item['title']} due to duplicate _id in candidates")
                    continue
                _id_set.add(exact_match[0]["_id"])
                item['best_score'] = 100
                item['closest_title'] = exact_match[0]['title']
                bulk_updates.append(
                    UpdateOne({"_id": exact_match[0]["_id"]}, {"$set": item})
                )
                continue

            best_match, best_ratio = self._best_fuzzy_match(item, candidates, _id_set)
            if best_match:
                _id_set.add(best_match["_id"])
                item['best_score'] = best_ratio
                item['closest_title'] = best_match['title']
                bulk_updates.append(
                    UpdateOne({"_id": best_match["_id"]}, {"$set": item})
                )
            else:
                print(f"No match for {item['title']} inserting new")
                bulk_updates.append(
                    UpdateOne({"title": item["title"]}, {"$set": item}, upsert=True)
                )

        if bulk_updates and not self.testing:
            db["all_manga"].bulk_write(bulk_updates)

        return scans
