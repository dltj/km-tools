import json
import sqlite_utils
import click
import dateutil.parser
import requests


@click.command()
@click.pass_obj
def pinboard(details):
    """Update local Pinboard database"""

    params = {"format": "json", "auth_token": details.config.pinboard.auth_token}

    db = sqlite_utils.Database(details.config.pinboard.dbfile)

    if db["posts"].exists:
        since_date = db.conn.execute("SELECT max(time) FROM posts;").fetchone()[0]
    if since_date:
        params["fromdt"] = (
            dateutil.parser.parse(since_date)
            .replace(microsecond=0, tzinfo=None)
            .isoformat()
            + "Z"
        )

    posts = requests.get("https://api.pinboard.in/v1/posts/all", params=params).json()
    _save_posts(db, posts)


def _save_posts(db, posts):
    # Convert/coerce some fields
    for post in posts:
        post["shared"] = post["shared"] == "yes"
        post["toread"] = post["toread"] == "yes"
        post["time"] = dateutil.parser.parse(post["time"])
        post["tags"] = json.dumps(post["tags"].split())

    db["posts"].upsert_all(
        posts,
        pk="hash",
        column_order=[
            "hash",
            "href",
            "description",
            "extended",
            "meta",
            "time",
            "shared",
            "toread",
            "tags",
        ],
    )
