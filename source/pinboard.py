import json

import click
import dateutil.parser
import exceptions
import requests
from config import config

from source import Origin, OriginTuple, Webpage, WebResource




@click.group()
def pinboard():
    """Commands for Pinboard"""


@pinboard.command(name="fetch")
@click.pass_obj
def fetch_command(ctx_obj):
    """Retrieve annotations"""
    return fetch(ctx_obj)


def register_origin():
    return OriginTuple(new_entries, save_entry)


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
            "",  # posted_to_twitter
            "",  # archive_url
            "",  # obsidian file path
            "",  # mastodon url
            "",  # derived date
            "",  # summarization
        ]

        query = f"REPLACE INTO pinb_posts VALUES ({','.join('?' * len(values))})"
        replace_cur.execute(query, values)
        ctx_obj.logger.info(f"Added {bookmark['href']} from {bookmark['time']}.")
        db.commit()


def find_entry(details, href):
    db = details.kmtools_db
    search_cur = db.cursor()
    query = "SELECT * FROM pinb_posts WHERE href=:href"
    search_cur.execute(query, [href])
    row = search_cur.fetchone()
    if row:
        webpage = Webpage(
            row["hash"],
            row["href"],
            row["description"],
            row["extended"],
            row["tags"],
            None,
            row["archive_url"],
            row["time"],
            row["derived_date"],
            row["summarization"],
        )
        if search_cur.fetchone():
            raise exceptions.MoreThanOneError
    else:
        webpage = None
    return webpage


def new_entries(details, db_column):
    new_rows = []

    db = details.kmtools_db
    search_cur = db.cursor()
    query = f"SELECT * FROM pinb_posts WHERE shared=1 AND LENGTH({db_column})<1 ORDER BY time"

    for row in search_cur.execute(query):
        webpage = Webpage(
            row["hash"],
            row["href"],
            row["description"],
            row["extended"],
            row["tags"],
            None,
            row["archive_url"],
            row["time"],
            row["derived_date"],
            row["summarization"],
        )
        new_rows.append(webpage)

    return new_rows


def save_entry(details, db_column, ident, stored_value):
    db = details.kmtools_db
    update_cur = db.cursor()
    query = f"UPDATE pinb_posts SET {db_column}=? WHERE href=?"
    values = [stored_value, ident]
    update_cur.execute(query, values)
    db.commit()


def get_wayback_jobs(details):
    """Get in-progress Wayback Job IDs from Pinboard database.

    :returns: list of job ids
    """
    job_entries = []

    db = details.kmtools_db
    search_cur = db.cursor()
    query = "SELECT * FROM pinb_posts WHERE archive_url NOT LIKE 'https://web.archive.org%' AND archive_url NOT LIKE 'https://archive.is%'"

    for row in search_cur.execute(query):
        job_entries.append(row["archive_url"])

    return job_entries


def get_unsummarized(details):
    """Return URLs of rows that do not have summaries

    :returns: list of URLs
    """

    unsummarized_entries = []
    db = details.kmtools_db
    search_cur = db.cursor()
    query = "SELECT * FROM pinb_posts WHERE LENGTH(summarization)<1 ORDER BY time"
    for row in search_cur.execute(query):
        unsummarized_entries.append(row["href"])

    return unsummarized_entries


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
   tweet_url TEXT,
   archive_url TEXT,
   obsidian_date TEXT,
   toot_url TEXT,
   derived_date TEXT,
   summarization TEXT
);
"""
