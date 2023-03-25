"""_Wayback commands_"""
import logging

import click

from kmtools.action.wayback import wayback_action

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
