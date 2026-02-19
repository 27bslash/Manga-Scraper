import json
import os
import time

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from db import db

load_dotenv()


def _get_region() -> str:
    return os.getenv("AWS_REGION", "eu-west-2")


def _get_apigw_client():
    endpoint = os.getenv("WS_API_ENDPOINT")
    if not endpoint:
        print('no end point')
        return None
    return boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=endpoint,
        region_name=_get_region(),
    )


def _get_mongo_collection():
    collection_name = os.getenv("WS_CONNECTIONS_COLLECTION", "ws_connections")
    return db[collection_name]


def _get_pending_timeout_seconds() -> int:
    return max(1, int(os.getenv("WS_UPDATE_PENDING_TIMEOUT_SECONDS", "21600")))


def _build_connection_query(user_ids=None):
    now = int(time.time())
    stale_before = now - _get_pending_timeout_seconds()
    query = {
        "$and": [
            {"$or": [{"ttl": {"$exists": False}}, {"ttl": {"$gt": now}}]},
            {
                "$or": [
                    {"updatePending": {"$ne": True}},
                    {"updatePendingAt": {"$exists": False}},
                    {"updatePendingAt": {"$lte": stale_before}},
                ]
            },
        ]
    }
    if user_ids is None:
        return query
    filtered_users = [str(user_id) for user_id in set(user_ids) if user_id]
    if not filtered_users:
        return None
    query["$and"].append({"user": {"$in": filtered_users}})
    return query


def clear_pending_updates(user_ids) -> int:
    collection = _get_mongo_collection()
    if collection is None:
        return 0
    filtered_users = [str(user_id) for user_id in set(user_ids) if user_id]
    if not filtered_users:
        return 0
    result = collection.update_many(
        {"user": {"$in": filtered_users}},
        {"$unset": {"updatePending": "", "updatePendingAt": ""}},
    )
    return result.modified_count

def broadcast_event(payload: dict, user_ids=None) -> int:
    collection = _get_mongo_collection()
    apigw = _get_apigw_client()
    if collection is None or not apigw:
        print("WebSocket publish skipped: missing DB_CONNECTION or WS_API_ENDPOINT")
        return 0

    data = json.dumps(payload).encode("utf-8")
    sent = 0
    pending_started_at = int(time.time())
    query = _build_connection_query(user_ids=user_ids)
    if query is None:
        return 0

    sent_users = set()
    sent_connection_ids = []
    gone_connection_ids = []

    cursor = collection.find(query, {"connectionId": 1, "user": 1})
    for item in cursor:
        connection_id = item.get("connectionId")
        if not connection_id:
            print('no connection id')
            continue
        user = item.get("user")
        if user and user in sent_users:
            continue
        try:
            apigw.post_to_connection(ConnectionId=connection_id, Data=data)
            sent += 1
            if user:
                sent_users.add(user)
            else:
                sent_connection_ids.append(connection_id)
        except apigw.exceptions.GoneException:
            gone_connection_ids.append(connection_id)
        except ClientError as err:
            print(f"WebSocket publish error for {connection_id}: {err}")

    if sent_users:
        collection.update_many(
            {"user": {"$in": list(sent_users)}},
            {"$set": {"updatePending": True, "updatePendingAt": pending_started_at}},
        )
    if sent_connection_ids:
        collection.update_many(
            {"connectionId": {"$in": sent_connection_ids}},
            {"$set": {"updatePending": True, "updatePendingAt": pending_started_at}},
        )
    if gone_connection_ids:
        collection.delete_many({"connectionId": {"$in": gone_connection_ids}})

    return sent


def build_update_payload() -> dict:
    return {"type": "manga-updated", "time": time.time()}


if __name__ == '__main__':
    sent = broadcast_event(
        build_update_payload(),
        user_ids=['test'],
    )
    print(
        f"WebSocket notify sent to {sent} connections "
        f"for {len(['test'])} changed users"
    )
