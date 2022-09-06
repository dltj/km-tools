import datetime
import json
import logging
import re

import click
import exceptions
import requests
from config import config

from source import Annotation, Origin, WebResource

logger = logging.getLogger(__name__)


class HypothesisPageOrigin(Origin):
    origin_name = "HYPOTHESIS"
    origin_table = "hyp_pages"
    origin_key = "uri"

    def __init__(self) -> None:
        super().__init__()

    def make_resource(self, uri: str) -> WebResource:
        return HypothesisResource(uri=uri)


hypothesis_page_origin = HypothesisPageOrigin()
config.origins.append(hypothesis_page_origin)


class HypothesisResource(WebResource):
    origin = hypothesis_page_origin

    docdrop_url_scan = re.compile(
        r"""^https?://docdrop.org/video/(.*?)/?$          # YouTube video id (group 1)
    """,
        re.X,
    )

    def __init__(self, uri) -> None:
        db = config.kmtools_db
        search_cur = db.cursor()
        query = "SELECT * FROM hyp_pages WHERE uri=:uri"
        search_cur.execute(query, [uri])
        row = search_cur.fetchone()
        if row:
            if match := self.docdrop_url_scan.match(uri):
                annotation_url = uri
                uri = f"https://youtube.com/watch?v={match.group(1)}"
            else:
                annotation_url = f"https://via.hypothes.is/{uri}"
            super().__init__(
                uri=uri,
                title=row["title"],
                description=None,
                tags=None,
                public=(row["public"] == "1"),
            )
            if search_cur.fetchone():
                raise exceptions.MoreThanOneError(uri)
        else:
            raise exceptions.ResourceNotFoundError(uri)
        self.annotation_url = annotation_url


class HypothesisAnnotationOrigin(Origin):
    origin_name = "HYPOTHESIS"
    origin_table = "hyp_posts"
    origin_key = "link_html"

    def __init__(self) -> None:
        super().__init__()

    def make_resource(self, uri: str) -> WebResource:
        return HypothesisAnnotation(uri)


hypothesis_annotation_origin = HypothesisAnnotationOrigin()


class HypothesisAnnotation(Annotation):
    origin = hypothesis_annotation_origin

    def __init__(self, uri) -> None:
        db = config.kmtools_db
        search_cur = db.cursor()
        query = "SELECT * FROM hyp_posts WHERE link_html=:uri"
        search_cur.execute(query, [uri])
        row = search_cur.fetchone()
        if row:
            super().__init__(
                uri=row["link_html"],
                source=HypothesisResource(row["uri"]),
                title=row["document_title"],
                quote=row["quote"],
                annotation=row["annotation"],
                tags=json.loads(row["tags"]),
                public=(row["hidden"] == "0"),
            )
            if search_cur.fetchone():
                raise exceptions.MoreThanOneError(uri)
        else:
            raise exceptions.ResourceNotFoundError(uri)
        self.created_date = row["created"]
        self.updated_date = row["updated"]
        self.link_incontext = row["link_incontext"]

    def output_annotation(self, filepath):
        with (config.output_fd(filepath)) as output_fh:
            tags = _format_tags(self.tags)
            quote = self.quote.strip()
            annotation = self.annotation.strip()
            # headline = discussion = ""
            if annotation.startswith("##"):
                headline, _, discussion = annotation.partition("\n")
                headline = f"{headline}\n"
            else:
                headline = ""
                discussion = annotation.strip()
            if discussion:
                discussion = f"{discussion}\n\n"
            if tags:
                tags = f"- Tags:: {tags}\n"
            output_fh.write(
                f"{headline}"
                f"> {quote}\n\n"
                f"{discussion}"
                f"- Link to [Annotation]({self.link_incontext})\n{tags}\n"
            )


def _format_tags(tag_list):
    if tag_list:
        # Dash to space
        tag_list = map(lambda x: x.replace("-", " "), tag_list)
        # Non hashtags to links
        tag_list = map(lambda x: f"[[{x}]]" if x[0] != "#" else x, tag_list)
        tags = ", ".join(tag_list)
    else:
        tags = None
    return tags


@click.group()
def hypothesis():
    """Commands for Hypothes.is"""


@hypothesis.command(name="fetch")
@click.pass_obj
def fetch_command(details):
    """Retrieve annotations"""
    return fetch(details)


def fetch(details):
    """Update local Hypothesis database"""

    headers = {
        "Accept": "application/vnd.hypothesis.v1+json",
    }
    params = {
        "sort": "updated",
        "order": "asc",
        "user": details.settings.hypothesis.user,
    }

    db = details.kmtools_db

    since_cur = db.cursor()
    since_date = since_cur.execute("SELECT max(updated) FROM hyp_posts;").fetchone()[0]
    if since_date:
        params["search_after"] = since_date

    logger.debug(f"Calling Hypothesis with {headers} (plus auth) and {params}")
    headers["Authorization"] = f"Bearer {details.settings.hypothesis.api_token}"

    r = requests.get("https://api.hypothes.is/api/search", params=params)
    if r.status_code > 200:
        logger.info(f"Couldn't call Hypothesis: ({r.status_code}): {r.text}")
        raise exceptions.HypothesisError(r.status_code, r.text)

    replace_cur = db.cursor()

    for annotation in r.json()["rows"]:
        logger.debug(
            f"Got annotation {annotation['id']}, last updated {annotation['updated']}: {annotation=}"
        )
        ## Skip comments on other's annotations
        if "references" in annotation:
            logger.debug(f"Skipping...reference to {annotation['references']}")
            continue

        if "selector" in annotation["target"][0]:
            for selector in annotation["target"][0]["selector"]:
                if selector["type"] == "TextQuoteSelector":
                    quote = selector["exact"]
        else:
            quote = ""
        if "title" in annotation["document"]:
            title = annotation["document"]["title"][0]
        else:
            title = annotation["uri"].rsplit("/", 1)[-1].rsplit(".", 1)[0]
        values = [
            annotation["id"],
            annotation["uri"],
            annotation["text"],
            annotation["created"],
            annotation["updated"],
            quote,
            json.dumps(annotation["tags"]),
            title,
            annotation["links"]["html"],
            annotation["links"]["incontext"],
            int(annotation["hidden"] == True),  # noqa: E712, pylint: disable=C0121
            int(annotation["flagged"] == True),  # noqa: E712, pylint: disable=C0121
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
                    title,
                    1,  ## Is public
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S%z"),
                ]
                query = f"REPLACE INTO hyp_pages VALUES ({','.join('?' * len(values))})"
                replace_cur.execute(query, values)
                logger.debug("Added to pages table.")

        query = "REPLACE INTO hyp_posts_pages_map VALUES (?, ?)"
        values = [annotation["id"], annotation["uri"]]
        replace_cur.execute(query, values)
        logger.info(f"Added {annotation['uri']} from {annotation['updated']}.")
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

CREATE TABLE hyp_pages (
	uri TEXT PRIMARY KEY,
	title TEXT,
	public INTEGER DEFAULT 0,
);

CREATE TABLE hyp_posts_pages_map (
	uri TEXT NOT NULL,
	annotation_id TEXT NOT NULL,
	FOREIGN KEY (uri) REFERENCES pages(uri),
	FOREIGN KEY (annotation_id) REFERENCES posts(id),
	PRIMARY KEY (uri, annotation_id)
);
"""
