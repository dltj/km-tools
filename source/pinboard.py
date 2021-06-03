import json
import collections
import click
import dateutil.parser
import requests
import exceptions
from source import Source


@click.group()
def pinboard():
    """Commands for Pinboard"""


@pinboard.command(name="fetch")
@click.pass_obj
def fetch_command(details):
    """Retrieve annotations"""
    return fetch(details)


def register_source():
    return Source(new_entries, save_entry)


def fetch(details):
    """Update local Pinboard database"""

    params = {
        "format": "json",
    }

    db = details.kmtools_db

    since_cur = db.cursor()
    since_date = since_cur.execute("SELECT max(time) FROM pinb_posts;").fetchone()[0]
    if since_date:
        params["fromdt"] = (
            dateutil.parser.parse(since_date)
            .replace(microsecond=0, tzinfo=None)
            .isoformat()
            + "Z"
        )

    details.logger.debug(f"Calling Pinboard with {params} (plus auth)")
    params["auth_token"] = details.config.pinboard.auth_token

    r = requests.get("https://api.pinboard.in/v1/posts/all", params=params)
    if r.status_code > 200:
        details.logger.debug(f"Couldn't call Pinboard: ({r.status_code}): {r.text}")
        raise exceptions.PinboardError(r.status_code, r.text)

    replace_cur = db.cursor()

    for bookmark in r.json():
        details.logger.debug(
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
        ]

        query = f"REPLACE INTO pinb_posts VALUES ({','.join('?' * len(values))})"
        replace_cur.execute(query, values)
        details.logger.info(f"Added {bookmark['href']} from {bookmark['time']}.")
        db.commit()


def new_entries(details, db_column):
    new_rows = []
    Bookmark = collections.namedtuple(
        "Bookmark",
        [
            "hash_value",
            "href",
            "title",
        ],
    )

    db = details.kmtools_db
    search_cur = db.cursor()
    query = f"SELECT * FROM pinb_posts WHERE shared=1 AND LENGTH({db_column})<1 ORDER BY time"

    for row in search_cur.execute(query):
        bookmark = Bookmark(row["hash"], row["href"], row["description"])
        new_rows.append(bookmark)

    return new_rows


def save_entry(details, db_column, hash_value, tweet_url):
    db = details.kmtools_db
    update_cur = db.cursor()
    query = f"UPDATE pinb_posts SET {db_column}=? WHERE hash=?"
    values = [tweet_url, hash_value]
    update_cur.execute(query, values)
    db.commit()


def new_wayback(details):
    """Get a list of new URLs to save in the Wayback Machine.

    :param details: Context object

    :returns: list of URLs and save in Wayback
    """
    new_entries = []

    db = details.kmtools_db
    search_cur = db.cursor()
    query = "SELECT * FROM pinb_posts WHERE shared=1 AND LENGTH(archive_url)<1"

    for row in search_cur.execute(query):
        new_entries.append(row["href"])

    return new_entries


def get_wayback_jobs(details):
    """Get in-progress Wayback Job IDs from Pinboard database.

    :returns: list of job ids
    """
    job_entries = []

    db = details.kmtools_db
    search_cur = db.cursor()
    query = (
        "SELECT * FROM pinb_posts WHERE archive_url NOT LIKE 'https://web.archive.org%'"
    )

    for row in search_cur.execute(query):
        job_entries.append(row["archive_url"])

    return job_entries


def save_wayback(details, href, value):
    """Save state about Wayback Machine jobs in Hypothesis database.

    :param details: Context object
    :param href: string, URL being saved
    :param value: string, either a Wayback job id or a Wayback URL
    """
    db = details.kmtools_db
    update_cur = db.cursor()
    query = "UPDATE pinb_posts SET archive_url=? WHERE href=?"
    values = [value, href]
    update_cur.execute(query, values)
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
   tweet_url TEXT,
   archive_url TEXT);
"""
