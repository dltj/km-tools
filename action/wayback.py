"""Archive at Wayback"""
import collections

import click
import exceptions
import requests

from action import ActionTuple


@click.group()
def wayback():
    """Commands for Wayback Machine"""


@wayback.command(name="save")
@click.argument("url")
@click.pass_obj
def save_url_command(details, url=None):
    """Save URL to Wayback

    :param details: Context object
    :param url: URL to save in Wayback
    """
    if url:
        job_id = save_url(details, url)
        click.echo(f"Request to save '{url}' submitted (job id {job_id}).")
    else:
        click.echo("No URL submitted.")


@wayback.command(name="check")
@click.argument("job_id")
@click.pass_obj
def check_job_command(details, job_id=None):
    """Check the status of a Wayback job

    :param details: Context object
    :param job_id: Wayback Job ID string
    """
    if job_id:
        results = check_job(details, job_id)
        if results.completed:
            click.echo(
                f"Request for {results.original_url} is completed. "
                f"Find the saved web page at {results.wayback_url}"
            )
        if results.in_progress:
            click.echo("Request is still in progress.")
    else:
        click.echo("No job_id submitted.")


def register_hourly_action():
    return ActionTuple("archive_url", save_url)


# FIXME: Do better than this with the positional arguments
def save_url(details, url=None, discard1=None, discard2=None):
    """Archive at Wayback

    :param details: Context object
    :param url: str, URL to save in Wayback

    :returns: str, Wayback Job ID string
    """

    ## This conditional effectively skips saving Internet Archive URLs into wayback
    if url.startswith("https://archive.org/") or url.startswith("https://archive.is/"):
        return url

    wayback_headers = {
        "Accept": "application/json",
    }
    wayback_body = {
        "url": url,
        "capture_screenshot": 1,
        "delay_wb_availability": 1,
        "skip_first_archive": 1,
        "email_result": 0,
    }
    wayback_endpoint = "https://web.archive.org/save"
    details.logger.debug(
        f"Calling endpoint {wayback_endpoint}, headers {wayback_headers}, body {wayback_body}"
    )
    wayback_headers[
        "Authorization"
    ] = f"LOW {details.settings.wayback.access_key}:{details.settings.wayback.secret_key}"

    if not details.dry_run:  # pylint: disable=R1720
        r = requests.post(wayback_endpoint, headers=wayback_headers, data=wayback_body)
        details.logger.debug(f"Returned status {r.status_code}, '{r.text}'")
        if r.status_code == 200:
            details.logger.info(f"Successfully added {url} to Wayback")
            wayback_job = r.json()["job_id"]
            return wayback_job
        details.logger.info(f"Couldn't save url ({r.status_code}): {r.text}")
        raise exceptions.WaybackError(r.status_code, r.text)
    else:
        details.logger.info(f"Would have archived url: {url}")
    return None


def check_job(details, job_id=None):
    """Check status of Wayback archive job

    :param details: context object
    :param job_id: Wayback Machine job id

    :returns:
        - completed: bool, True if job is successful
        - in_progress: bool, True if job is in progress
        - status: str, Status value returned by Wayback
        - job_id: str, Wayback Job ID UUID
        - original_url: str, Original URL being saved
        - wayback_url: str, URL of page as saved in Wayback
        - timestamp: int, Timestamp in yyyymmddhhmmss form
        - complete status dictionary
    """

    wayback_headers = {
        "Accept": "application/json",
    }
    wayback_endpoint = f"https://web.archive.org/save/status/{job_id}"
    details.logger.debug(
        f"Calling endpoint {wayback_endpoint}, headers {wayback_headers}"
    )
    wayback_headers[
        "Authorization"
    ] = f"LOW {details.settings.wayback.access_key}:{details.settings.wayback.secret_key}"

    Wayback = collections.namedtuple(
        "Wayback",
        [
            "completed",
            "in_progress",
            "status",
            "job_id",
            "original_url",
            "wayback_url",
            "timestamp",
            "details",
        ],
    )
    if not job_id or len(job_id) == 0:
        return

    if not details.dry_run:  # pylint: disable=R1720
        r = requests.get(wayback_endpoint, headers=wayback_headers)
        details.logger.debug(f"Returned status {r.status_code}, '{r.text}'")
        if r.status_code == 200:
            wayback_details = r.json()
            wayback_status = wayback_details["status"]
            wayback_original_url = None
            if "original_url" in wayback_details:
                wayback_original_url = wayback_details["original_url"]
            wayback_timestamp = None
            wayback_url = None
            if "timestamp" in wayback_details:
                wayback_timestamp = wayback_details["timestamp"]
                wayback_url = f"https://web.archive.org/{wayback_timestamp}/{wayback_original_url}"
            details.logger.info(f"Job {job_id} is {wayback_status}")
            results = Wayback(
                wayback_status == "success",
                wayback_status == "pending",
                wayback_status,
                job_id,
                wayback_original_url,
                wayback_url,
                wayback_timestamp,
                wayback_details,
            )
            return results
        details.logger.info(
            f"Couldn't check status of {job_id} ({r.status_code}): {r.text}"
        )
        raise exceptions.WaybackError(r.status_code, r.text)
    else:
        details.logger.info(f"Would have checked status of: {wayback_endpoint}")
        results = Wayback(
            False, False, "dry-run", job_id, None, None, None, {"status": "dry-run"}
        )
        return results
    return None
