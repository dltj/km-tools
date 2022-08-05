import json

import click
import dateutil.parser
import exceptions
import requests
from config import config

from source import Origin, WebResource


class PinboardOrigin(Origin):
    origin_name = "PINBOARD"
    origin_table = "pinb_posts"
    origin_key = "href"
    obsidian_tagless = True

    def __init__(self) -> None:
        super().__init__()

    def make_resource(self, uri: str) -> WebResource:
        return PinboardResource(uri=uri)


pinboard_origin = PinboardOrigin()
config.origins.append(pinboard_origin)


class PinboardResource(WebResource):

    origin = pinboard_origin

    def __init__(self) -> None:
        super().__init__()
        pass

    def __init__(self, uri):
        db = config.kmtools_db
        search_cur = db.cursor()
        query = "SELECT * FROM pinb_posts WHERE href=:uri"
        search_cur.execute(query, [uri])
        row = search_cur.fetchone()
        if row:
            super().__init__(
                uri=uri,
                title=row["description"],
                description=row["extended"],
                tags=json.loads(row["tags"]),
                public=(row["shared"] == "1"),
            )
            if search_cur.fetchone():
                raise exceptions.MoreThanOneError(uri)
        else:
            raise exceptions.ResourceNotFoundError(uri)
        self.toread = row["toread"] == "1"


@click.group()
def pinboard():
    """Commands for Pinboard"""


@pinboard.command(name="fetch")
@click.pass_obj
def fetch_command(ctx_obj):
    """Retrieve annotations"""
    return fetch(ctx_obj)


def fetch(ctx_obj):
    """Update local Pinboard database"""

    params = {
        "format": "json",
    }

    db = ctx_obj.kmtools_db

    since_cur = db.cursor()
    since_date = since_cur.execute("SELECT max(time) FROM pinb_posts;").fetchone()[0]
    if since_date:
        params["fromdt"] = (
            dateutil.parser.parse(since_date)
            .replace(microsecond=0, tzinfo=None)
            .isoformat()
            + "Z"
        )

    ctx_obj.logger.debug(f"Calling Pinboard with {params} (plus auth)")
    params["auth_token"] = ctx_obj.settings.pinboard.auth_token

    r = requests.get("https://api.pinboard.in/v1/posts/all", params=params)
    if r.status_code > 200:
        ctx_obj.logger.debug(f"Couldn't call Pinboard: ({r.status_code}): {r.text}")
        raise exceptions.PinboardError(r.status_code, r.text)

    replace_cur = db.cursor()

    for bookmark in r.json():
        ctx_obj.logger.debug(
            f"Got annotation {bookmark['href']}, last updated {bookmark['time']}"
        )

        values = [
            bookmark["hash"],
            bookmark["href"],
            bookmark["description"],
            bookmark["extended"],
            bookmark["meta"],
            dateutil.parser.parse(bookmark["time"]),
            bookmark["shared"] == "yes",
            bookmark["toread"] == "yes",
            json.dumps(bookmark["tags"].split()),
        ]

        query = f"REPLACE INTO pinb_posts VALUES ({','.join('?' * len(values))})"
        replace_cur.execute(query, values)
        ctx_obj.logger.info(f"Added {bookmark['href']} from {bookmark['time']}.")
        db.commit()


"""
CREATE TABLE pinb_posts (
   hash TEXT PRIMARY KEY,
   href TEXT,
   description TEXT,
   extended TEXT,
   meta TEXT,
   time TEXT,
   shared INTEGER,
   toread INTEGER,
   tags TEXT,
);
"""
