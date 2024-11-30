import logging
from sqlite3 import IntegrityError

import click
import requests
from dateutil.parser import isoparse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from kmtools import exceptions
from kmtools.models import Pinboard, VisibilityEnum
from kmtools.util import database

logger = logging.getLogger(__name__)


def get_or_create_pinboard(session, href, title, time):
    try:
        # Query to check if the Pinboard object already exists
        stmt = select(Pinboard).where(Pinboard.href == href)
        existing_pinboard = session.execute(stmt).scalars().first()

        if existing_pinboard:
            logger.info(
                "Found existing Pinboard object for %s: %s", href, existing_pinboard
            )
            return existing_pinboard
        else:
            # If not exists, create a new one
            logger.info("Creating new Pinboard object for %s", href)
            new_pinboard = Pinboard(href=href)
            session.add(new_pinboard)
            return new_pinboard

    except IntegrityError:
        # Handle potential race conditions, retry fetch
        session.rollback()
        return session.execute(stmt).scalars().first()


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

    with Session(database.engine) as session:
        # Query the most recent Pinboard entry based on the 'time' column
        stmt = select(Pinboard).order_by(desc(Pinboard.saved_timestamp)).limit(1)

        # Execute the query
        most_recent_pinboard = session.execute(stmt).scalars().first()
        since_date = most_recent_pinboard.saved_timestamp
        if since_date:
            params["fromdt"] = (
                since_date.replace(microsecond=0, tzinfo=None).isoformat() + "Z"
            )

        logger.debug("Calling Pinboard with %s (plus auth)", params)
        params["auth_token"] = ctx_obj.settings.pinboard.auth_token

        r = requests.get(
            "https://api.pinboard.in/v1/posts/all", params=params, timeout=30
        )
        if r.status_code > 200:
            logger.debug("Couldn't call Pinboard: (%s): %s", r.status_code, r.text)
            raise exceptions.PinboardError(r.status_code, r.text)
        logger.debug("Got response from Pinboard")

        for bookmark in r.json():
            logger.debug(
                "Got bookmark %s, last updated %s", bookmark["href"], bookmark["time"]
            )
            new_pinboard = get_or_create_pinboard(
                session,
                bookmark["href"],
                bookmark["description"],
                isoparse(bookmark["time"]),
            )
            new_pinboard.hash = bookmark["hash"]
            new_pinboard.title = bookmark["description"]
            new_pinboard.description = bookmark["extended"]
            new_pinboard.meta = bookmark["meta"]
            new_pinboard.saved_timestamp = isoparse(bookmark["time"])
            new_pinboard.toread = bookmark["toread"]
            new_pinboard.tags = [
                tag.replace("-", " ") for tag in bookmark["tags"].split(" ")
            ]
            if bookmark["shared"]:
                new_pinboard.shared = VisibilityEnum.PUBLIC
            else:
                new_pinboard.shared = VisibilityEnum.PRIVATE
            session.commit()


# CREATE TABLE pinb_posts (
#    hash TEXT PRIMARY KEY,
#    href TEXT,
#    description TEXT,
#    extended TEXT,
#    meta TEXT,
#    time TEXT,
#    shared INTEGER,
#    toread INTEGER,
#    tags TEXT,
# );
