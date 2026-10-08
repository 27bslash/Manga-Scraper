import traceback

from db import db


LOW_PRIORITY_SOURCES = ("mangadex","reddit")


class SourceMerger:
    """Merges per-site source entries into the stored all_manga documents."""

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
            true_source_links = {
                item["latest_link"]
                for item in latest_sort
                if item.get("scansite")
                and item["scansite"] not in LOW_PRIORITY_SOURCES
                and item.get("latest_link")
            }
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
                    scansite = item["scansite"]
                    if (
                        scansite in LOW_PRIORITY_SOURCES
                        and item.get("latest_link") in true_source_links
                    ):
                        continue
                    updated_sources[scansite] = source_string
                except KeyError:
                    print("e", item)
            return updated_sources
        except Exception as e:
            print(traceback.format_exc())
