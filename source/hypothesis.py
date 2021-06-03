import collections
import json
import requests
import click
import exceptions
from source import Source


@click.group()
def hypothesis():
    """Commands for Hypothes.is"""


@hypothesis.command(name="fetch")
@click.pass_obj
def fetch_command(details):
    """Retrieve annotations"""
    return fetch(details)


def register_source():
    return Source(new_entries, save_entry)


def fetch(details):
    """Update local Hypothesis database"""

    headers = {
        "Accept": "application/vnd.hypothesis.v1+json",
    }
    params = {
        "sort": "updated",
        "order": "asc",
        "user": details.config.hypothesis.user,
    }

    db = details.kmtools_db

    since_cur = db.cursor()
    since_date = since_cur.execute("SELECT max(updated) FROM hyp_posts;").fetchone()[0]
    if since_date:
        params["search_after"] = since_date

    details.logger.debug(f"Calling Hypothesis with {headers} (plus auth) and {params}")
    headers["Authorization"] = f"Bearer {details.config.hypothesis.api_token}"

    r = requests.get("https://api.hypothes.is/api/search", params=params)
    if r.status_code > 200:
        details.logger.info(f"Couldn't call Hypothesis: ({r.status_code}): {r.text}")
        raise exceptions.HypothesisError(r.status_code, r.text)

    replace_cur = db.cursor()

    for annotation in r.json()["rows"]:
        details.logger.debug(
            f"Got annotation {annotation['id']}, last updated {annotation['updated']}"
        )
        ## Skip comments on other's annotations
        if "references" in annotation:
            details.logger.debug(f"Skipping...reference to {annotation['references']}")
            continue

        for selector in annotation["target"][0]["selector"]:
            if selector["type"] == "TextQuoteSelector":
                quote = selector["exact"]
        values = [
            annotation["id"],
            annotation["uri"],
            annotation["text"],
            annotation["created"],
            annotation["updated"],
            quote,
            f"{json.dumps(annotation['tags']).split()}",
            annotation["document"]["title"][0],
            annotation["links"]["html"],
            annotation["links"]["incontext"],
            int(annotation["hidden"] == True),  # noqa: E712, pylint: disable=C0121
            int(annotation["flagged"] == True),  # noqa: E712, pylint: disable=C0121
            0,  ## Last column is posted_to_obsidian, which we want to be false
        ]
        query = f"REPLACE INTO hyp_posts VALUES ({','.join('?' * len(values))})"
        replace_cur.execute(query, values)

        if "group:__world__" in annotation["permissions"]["read"]:
            query = "SELECT * FROM hyp_pages WHERE uri=?"
            values = [annotation["uri"]]
            check = replace_cur.execute(query, values)
            match = check.fetchone()
            if not match or (match and match["public"] == 0):
                values = [
                    annotation["uri"],
                    annotation["document"]["title"][0],
                    1,  ## Is public
                    "",  ## Has not been posted to twitter
                    "",  ## Has not been saved to archive
                ]
                query = "REPLACE INTO hyp_pages VALUES (?, ?, ?, ?, ?)"
                replace_cur.execute(query, values)
                details.logger.debug("Added to pages table.")

        query = "REPLACE INTO hyp_posts_pages_map VALUES (?, ?)"
        values = [annotation["id"], annotation["uri"]]
        replace_cur.execute(query, values)
        details.logger.info(f"Added {annotation['uri']} from {annotation['updated']}.")
        db.commit()


def new_entries(details, db_column):
    new_rows = []
    Annotation = collections.namedtuple(
        "Bookmark",
        [
            "href",
            "title",
        ],
    )

    db = details.kmtools_db
    search_cur = db.cursor()
    query = "SELECT * FROM hyp_pages WHERE public=1 AND LENGTH(?)<1"
    values = [db_column]

    for row in search_cur.execute(query, values):
        new_rows.append(Annotation([row["uri"], row["title"]]))

    return new_rows


def save_entry(details, db_column, uri, tweet_url):
    db = details.kmtools_db
    update_cur = db.cursor()
    query = "UPDATE hyp_pages SET ?=? WHERE uri=?"
    values = [db_column, tweet_url, uri]
    update_cur.execute(query, values)
    db.commit()


def new_wayback(details):
    """Get a list of new URLs to save in the Wayback Machine.

    :param details: Context object

    :returns: list of URLs and save in Wayback
    """
    new_rows = []

    db = details.kmtools_db
    search_cur = db.cursor()
    query = "SELECT * FROM hyp_pages WHERE public=1 AND LENGTH(archive_url)<1"

    for row in search_cur.execute(query):
        new_rows.append(row["uri"])

    return new_rows


def get_wayback_jobs(details):
    """Get in-progress Wayback Job IDs from Hypothesis database.

    :returns: list of job ids
    """
    job_entries = []

    db = details.kmtools_db
    search_cur = db.cursor()
    query = (
        "SELECT * FROM hyp_pages WHERE archive_url NOT LIKE 'https://web.archive.org%'"
    )

    for row in search_cur.execute(query):
        job_entries.append(row["archive_url"])

    return job_entries


def save_wayback(details, uri, value):
    """Save state about Wayback Machine jobs in Hypothesis database.

    :param details: Context object
    :param uri: string, URL being saved
    :param value: string, either a Wayback job id or a Wayback URL
    """
    db = details.kmtools_db
    update_cur = db.cursor()
    query = "UPDATE hyp_pages SET archive_url=? WHERE uri=?"
    values = [value, uri]
    update_cur.execute(query, values)
    db.commit()


"""
CREATE TABLE hyp_posts (
	id TEXT PRIMARY KEY,
	uri TEXT NOT NULL,
	annotation TEXT,
	created TEXT,
	updated TEXT,
	quote TEXT,
	tags TEXT,
	document_title TEXT,
	link_html TEXT,
	link_incontext INTEGER,
	hidden INTEGER,
	flagged INTEGER,
	posted_to_obsidian INTEGER DEFAULT 0);
    
CREATE TABLE hyp_pages (
	uri TEXT PRIMARY KEY,
	title TEXT,
	public INTEGER DEFAULT 0,
	tweet_url TEXT,
	archive_url TEXT
);

CREATE TABLE hyp_posts_pages_map (
	uri TEXT NOT NULL,
	annotation_id TEXT NOT NULL,
	FOREIGN KEY (uri) REFERENCES pages(uri),
	FOREIGN KEY (annotation_id) REFERENCES posts(id),
	PRIMARY KEY (uri, annotation_id)
);
"""
