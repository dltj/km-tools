"""_Wayback commands_"""

import logging
from datetime import datetime
from typing import List

import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from kmtools.action.wayback_action import ResultsFromWaybackAction
from kmtools.models import ProcessStatus, ProcessStatusEnum, WebResource
from kmtools.util import database

logger = logging.getLogger(__name__)


@click.group()
def wayback():
    """Commands for Wayback Machine"""


def _mark_completed(session: Session, resource: WebResource) -> None:
    proc_status: ProcessStatus | None = (
        session.execute(
            select(ProcessStatus).where(
                ProcessStatus.resource == resource,
                ProcessStatus.action_name == ResultsFromWaybackAction.action_name,
            )
        )
        .scalars()
        .first()
    )
    if not proc_status:
        logger.warning(
            "No ProcessStatus found for resource %s, action %s",
            resource.id,
            ResultsFromWaybackAction.action_name,
        )
        return
    proc_status.status = ProcessStatusEnum.COMPLETED
    proc_status.retries = -2


@wayback.command(name="hung")
def hung_jobs():
    """List hung Wayback jobs"""
    with database.get_session() as session:
        stmt = (
            select(WebResource)
            .join(ProcessStatus, WebResource.id == ProcessStatus.resource_id)
            .where(
                ProcessStatus.status == ProcessStatusEnum.RETRIES_EXCEEDED,
                ProcessStatus.action_name == ResultsFromWaybackAction.action_name,
            )
        )
        stalled_rows: List[WebResource] = session.execute(stmt).scalars().all()

        if stalled_rows:
            fmt_str = "{:10.10s} {:13.13s}  {:31.31s}  {:s}"
            for row in stalled_rows:
                click.echo(fmt_str.format("Resource", "Origin", "Saved", "URL"))
                click.echo("Wayback URL\n")
                click.echo(
                    fmt_str.format(
                        str(row.id),
                        row.discriminator,
                        row.saved_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        row.url,
                    ),
                )
                try:
                    wayback_year = row.saved_timestamp.year
                except (AttributeError, TypeError):
                    wayback_year = datetime.now().year

                click.echo(f"https://web.archive.org/web/{wayback_year}*/{row.url}\n")
                new_archive_url = click.prompt(
                    "Enter replacement URL (or return to skip)", type=str, default=""
                )
                if new_archive_url:
                    row.action_wayback.wayback_url = new_archive_url
                    _mark_completed(session, row)
                    session.commit()
                else:
                    if click.confirm("Artificially mark as complete?"):
                        _mark_completed(session, row)
        else:
            click.echo(click.style("No hung jobs found.", fg="green"))
