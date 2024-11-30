"""_Wayback commands_"""

import logging
from typing import List

import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from kmtools.action.wayback import wayback_action
from kmtools.action.wayback_action import ResultsFromWaybackAction
from kmtools.models import ProcessStatus, ProcessStatusEnum, WebResource
from kmtools.util import database

logger = logging.getLogger(__name__)


@click.group()
def wayback():
    """Commands for Wayback Machine"""


@wayback.command(name="save")
@click.argument("url")
def save_url_command(url=None):
    """Save URL to Wayback

    :param details: Context object
    :param url: URL to save in Wayback
    """
    if url:
        job_id = wayback_action.url_action(url=url)
        # job_id = save_url(url)
        click.echo(f"Request to save '{url}' submitted (job id {job_id}).")
    else:
        click.echo("No URL submitted.")


@wayback.command(name="check")
@click.argument("job_id")
def check_job_command(job_id=None):
    """Check the status of a Wayback job

    :param details: Context object
    :param job_id: Wayback Job ID string
    """
    if job_id:
        results = wayback_action.check_job(job_id)
        if results.completed:
            click.echo(
                f"Request for {results.original_url} is completed. "
                f"Find the saved web page at {results.wayback_url}"
            )
        if results.in_progress:
            click.echo("Request is still in progress.")
    else:
        click.echo("No job_id submitted.")


@wayback.command(name="update")
@click.argument("job_id")
def update_job_command(job_id=None):
    """Update the status of a Wayback job

    :param details: Context object
    :param job_id: Wayback Job ID string
    """
    if job_id:
        message = wayback_action.update_job(job_id)
        click.echo(message)


def _mark_completed(session: Session, resource: WebResource) -> None:
    proc_status: ProcessStatus = (
        session.execute(
            select(ProcessStatus).where(
                ProcessStatus.resource == resource,
                ProcessStatus.action_name == ResultsFromWaybackAction.action_name,
            )
        )
        .scalars()
        .first()
    )
    proc_status.status = ProcessStatusEnum.COMPLETED
    proc_status.retries = -2


@wayback.command(name="hung")
def hung_jobs():
    """List hung Wayback jobs"""
    with Session(database.engine) as session:
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
                click.echo(f"https://web.archive.org/web/2024*/{row.url}\n")
                new_archive_url = click.prompt(
                    "Enter replacement URL (or return to skip)", type=str
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
