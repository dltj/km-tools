import json
import requests
import click
import exceptions
from source import Source, Webpage, Annotation


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
            json.dumps(annotation["tags"]),
            annotation["document"]["title"][0],
            annotation["links"]["html"],
            annotation["links"]["incontext"],
            int(annotation["hidden"] == True),  # noqa: E712, pylint: disable=C0121
            int(annotation["flagged"] == True),  # noqa: E712, pylint: disable=C0121
            "",  # obsidian path to file
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
                    "",  # Twitter URL (when posted)
                    "",  # Wayback URL (when saved)
                    "",  # Mastodon URL (when tooted)
                ]
                query = "REPLACE INTO hyp_pages VALUES (?, ?, ?, ?, ?, ?)"
                replace_cur.execute(query, values)
                details.logger.debug("Added to pages table.")

        query = "REPLACE INTO hyp_posts_pages_map VALUES (?, ?)"
        values = [annotation["id"], annotation["uri"]]
        replace_cur.execute(query, values)
        details.logger.info(f"Added {annotation['uri']} from {annotation['updated']}.")
        db.commit()


def new_entries(details, db_column):
    new_rows = []

    db = details.kmtools_db
    search_cur = db.cursor()
    query = f"SELECT * FROM hyp_pages WHERE public=1 AND LENGTH({db_column})<1"

    for row in search_cur.execute(query):
        webpage = Webpage(
            row["uri"],
            row["uri"],
            row["title"],
            None,
            None,
            f"https://via.hypothes.is/{row['uri']}",
        )
        new_rows.append(webpage)

    return new_rows


def save_entry(details, db_column, ident, stored_value):
    db = details.kmtools_db
    update_cur = db.cursor()
    query = f"UPDATE hyp_pages SET {db_column}=? WHERE uri=?"
    values = [stored_value, ident]
    update_cur.execute(query, values)
    db.commit()


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


def get_new_annotations(details):
    """Get an iterator of new Hypothesis annotations

    :param details: context object

    :returns: an Annotation
    """
    db = details.kmtools_db
    search_cur = db.cursor()
    query = "SELECT * FROM hyp_posts WHERE LENGTH(obsidian_file)<1 ORDER BY updated"

    for row in search_cur.execute(query):
        yield (
            Annotation(
                row["id"],
                row["uri"],
                row["annotation"],
                row["created"],
                row["updated"],
                row["quote"],
                row["tags"],
                row["document_title"],
                row["link_html"],
                row["link_incontext"],
                row["hidden"],
                row["flagged"],
            )
        )


def save_annotation(details, uri, location):
    """Save where an annotation has been saved in Obsidian.

    :param details: context object
    :param id: id of the annotation
    :param location: file path to the Obsidian file

    :returns: None
    """
    db = details.kmtools_db
    update_cur = db.cursor()
    query = "UPDATE hyp_posts SET obsidian_file=? WHERE id=?"
    values = [location, uri]
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
	obsidian_file TEXT);
    
CREATE TABLE hyp_pages (
	uri TEXT PRIMARY KEY,
	title TEXT,
	public INTEGER DEFAULT 0,
	tweet_url TEXT,
	archive_url TEXT,
   toot_url TEXT
);

CREATE TABLE hyp_posts_pages_map (
	uri TEXT NOT NULL,
	annotation_id TEXT NOT NULL,
	FOREIGN KEY (uri) REFERENCES pages(uri),
	FOREIGN KEY (annotation_id) REFERENCES posts(id),
	PRIMARY KEY (uri, annotation_id)
);
"""
