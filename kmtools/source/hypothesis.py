import logging

import click
import requests
from dateutil.parser import isoparse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from kmtools import exceptions
from kmtools.models import HypothesisAnnotation, VisibilityEnum
from kmtools.util import database

logger = logging.getLogger(__name__)


# def output_annotation(self, filepath):
#     with (config.output_fd(filepath)) as output_fh:
#         tags = _format_tags(self.tags)
#         quote = self.quote.strip()
#         annotation = self.annotation.strip()
#         # headline = discussion = ""
#         if annotation.startswith("##"):
#             headline, _, discussion = annotation.partition("\n")
#             headline = f"{headline}\n"
#         else:
#             headline = ""
#             discussion = annotation.strip()
#         if discussion:
#             discussion = f"{discussion}\n\n"
#         if tags:
#             tags = f"- Tags:: {tags}\n"
#         output_fh.write(
#             f"{headline}"
#             f"> {quote}\n\n"
#             f"{discussion}"
#             f"- Link to [Annotation]({self.link_incontext})\n{tags}\n"
#         )


# def _format_tags(tag_list):
#     if tag_list:
#         # Dash to space
#         tag_list = map(lambda x: x.replace("-", " "), tag_list)
#         # Non hashtags to links
#         tag_list = map(lambda x: f"[[{x}]]" if x[0] != "#" else x, tag_list)
#         tags = ", ".join(tag_list)
#     else:
#         tags = None
#     return tags


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

    with Session(database.engine) as session:
        # Query the most recent Pinboard entry based on the 'time' column
        stmt = (
            select(HypothesisAnnotation)
            .order_by(desc(HypothesisAnnotation.time_updated))
            .limit(1)
        )

        # Execute the query. We're using `microseconds=999999` as a
        # kluge to get past the most recent annotaion in the database.
        most_recent_annotation = session.execute(stmt).scalars().first()
        since_date = most_recent_annotation.time_updated
        if since_date:
            params["search_after"] = (
                since_date.replace(microsecond=999999, tzinfo=None).isoformat() + "Z"
            )

        logger.debug("Calling Hypothesis with %s (plus auth) and %s", headers, params)
        headers["Authorization"] = f"Bearer {details.settings.hypothesis.api_token}"

        r = requests.get(
            "https://api.hypothes.is/api/search",
            headers=headers,
            params=params,
            timeout=20,
        )
        if r.status_code > 200:
            logger.info("Couldn't call Hypothesis: (%s): %s", r.status_code, r.text)
            raise exceptions.HypothesisError(r.status_code, r.text)

    for annotation in r.json()["rows"]:
        logger.debug(
            "Got annotation %s, last updated %s",
            annotation["id"],
            annotation["updated"],
        )
        ## Skip comments on other's annotations
        if "references" in annotation:
            logger.debug("Skipping...reference to %s", annotation["references"])
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

        with session.no_autoflush:
            hypothesis_annotation, hypothesis_page = (
                HypothesisAnnotation.create_with_page(
                    session, annotation["uri"], title, isoparse(annotation["created"])
                )
            )
            hypothesis_annotation.hyp_id = annotation["id"]
            hypothesis_annotation.annotation = annotation["text"]
            hypothesis_annotation.time_updated = isoparse(annotation["updated"])
            hypothesis_annotation.quote = quote
            hypothesis_annotation.tags = annotation["tags"]
            hypothesis_annotation.link_html = annotation["links"]["html"]
            hypothesis_annotation.link_incontext = annotation["links"]["incontext"]
            hypothesis_annotation.shared = (
                VisibilityEnum.PRIVATE
                if annotation["hidden"]
                else VisibilityEnum.PUBLIC
            )
            hypothesis_annotation.flagged = int(annotation["flagged"] == True)

            hypothesis_page.shared = (
                VisibilityEnum.PRIVATE
                if annotation["hidden"]
                else VisibilityEnum.PUBLIC
            )

        # TODO: Is this important?
        # if "group:__world__" in annotation["permissions"]["read"]:
        session.commit()
        logger.info("Added %s from %s.", annotation["uri"], annotation["updated"])


# CREATE TABLE hyp_posts (
# 	id TEXT PRIMARY KEY,
# 	uri TEXT NOT NULL,
# 	annotation TEXT,
# 	created TEXT,
# 	updated TEXT,
# 	quote TEXT,
# 	tags TEXT,
# 	document_title TEXT,
# 	link_html TEXT,
# 	link_incontext INTEGER,
# 	hidden INTEGER,
# 	flagged INTEGER,

# CREATE TABLE hyp_pages (
# 	uri TEXT PRIMARY KEY,
# 	title TEXT,
# 	public INTEGER DEFAULT 0,
# );

# CREATE TABLE hyp_posts_pages_map (
# 	uri TEXT NOT NULL,
# 	annotation_id TEXT NOT NULL,
# 	FOREIGN KEY (uri) REFERENCES pages(uri),
# 	FOREIGN KEY (annotation_id) REFERENCES posts(id),
# 	PRIMARY KEY (uri, annotation_id)
# );
