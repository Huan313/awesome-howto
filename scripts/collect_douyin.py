"""Optional official Douyin hotsearch adapter for an approved app."""
import os
from uuid import uuid4

from scripts.common import FetchError, stamp

HOT_URL = "https://open.douyin.com/hotsearch/sentences/"
TOKEN_URL = "https://open.douyin.com/oauth/client_token/"


def units(config, end):
    credentials = os.getenv("DOUYIN_CLIENT_TOKEN") or (
        os.getenv("DOUYIN_CLIENT_KEY") and os.getenv("DOUYIN_CLIENT_SECRET"))
    if os.getenv(config["enabled_by"]) == "true" and credentials:
        yield "实时热点词", lambda client: collect(client, end)


def api_data(response):
    data = response.get("data", {})
    if str(data.get("error_code")) != "0":
        raise FetchError("Douyin rejected the request; check application capability and token")
    return data


def collect(client, end):
    token = os.getenv("DOUYIN_CLIENT_TOKEN")
    if not token:
        key, secret = os.getenv("DOUYIN_CLIENT_KEY"), os.getenv("DOUYIN_CLIENT_SECRET")
        if not (key and secret):
            raise FetchError("enabled without approved application credentials")
        boundary = uuid4().hex
        fields = dict(client_key=key, client_secret=secret, grant_type="client_credential")
        parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
                 for name, value in fields.items()]
        payload = ("".join(parts) + f"--{boundary}--\r\n").encode("utf-8")
        response = client.json(TOKEN_URL, {"Content-Type": f"multipart/form-data; boundary={boundary}"}, payload)
        token = api_data(response)["access_token"]
    for item in api_data(client.json(HOT_URL, {"access-token": token, "Content-Type": "application/json"}))["list"][:40]:
        query = item["sentence"]
        yield dict(platform="douyin", title=query, url="https://www.douyin.com/hot",
                   query=query, method="authorized-api", observed_at=stamp(end),
                   metrics={"heat": item.get("hot_level")})
