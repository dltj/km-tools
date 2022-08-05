"""Archive at Wayback"""
import collections
import json

import click
import exceptions
import requests
from config import config
from source import Origin, Resource
from source.pinboard import PinboardResource

from action import Action


class Wayback(Action):

    attributes_supplied = ("wayback_url", "wayback_timestamp", "wayback_details")
    action_table = "action_wayback"

    def __init__(self) -> None:
        super().__init__()

    def url_action(self, source: PinboardResource):
        """Archive at Wayback

        :param url: str, URL to save in Wayback

        :returns: None
        """

        ## This conditional effectively skips saving Internet Archive URLs into wayback
        if (
            source.url.startswith("https://archive.org/")
            or source.url.startswith("https://archive.is/")
            or source.url.startswith("https://archive.ph/")
        ):
            return source.url

        wayback_headers = {
            "Accept": "application/json",
        }
        wayback_body = {
            "url": source.uri,
            "capture_screenshot": 1,
            "delay_wb_availability": 1,
            "skip_first_archive": 1,
            "email_result": 0,
        }
        wayback_endpoint = "https://web.archive.org/save"
        config.logger.debug(
            f"Calling {wayback_endpoint}, {wayback_headers=} (plus auth), {wayback_body=}"
        )
        wayback_headers[
            "Authorization"
        ] = f"LOW {config.settings.wayback.access_key}:{config.settings.wayback.secret_key}"

        if config.dry_run:  # pylint: disable=R1720
            config.logger.info(f"Couldn't save url ({r.status_code}): {r.text}")
            return

        r = requests.post(wayback_endpoint, headers=wayback_headers, data=wayback_body)
        config.logger.debug(f"Wayback returned status {r.status_code}, '{r.text}'")
        if r.status_code != 200:
            config.logger.error(f"Couldn't save url ({r.status_code}): {r.text}")
            raise exceptions.WaybackError(r.status_code, r.text)
        wayback_response = r.json()
        wayback_job = wayback_response["job_id"]
        if "message" in wayback_response:
            config.logger.warning(f"Wayback said: {wayback_response['message']}")
            return wayback_job

        config.logger.info(f"Successfully added {source.uri} to Wayback")
        Action._save_attributes(self, source, ["wayback_url"], [wayback_job])
        return wayback_job

    def attribute_read(self, source: Resource, name: str) -> str:
        return Action._attribute_read(self, name, self.action_table, source.uri)

    def update_jobs(self):
        """For all uncompleted jobs, update the job status.

        :returns: None
        """
        db = config.kmtools_db
        search_cur = db.cursor()
        query = f"SELECT * FROM {self.action_table} WHERE wayback_url LIKE 'spn2-%'"
        for row in search_cur.execute(query):
            config.logger.info(f"Checking status of {row['url']}")
            self.update_job(row["wayback_url"])

    def update_job(self, wayback_job=None):
        """Get the status of the Wayback job and update the table if necessary.

        :param job_id: Wayback Machine job id

        :returns: Textual statement of status
        """
        if results := self.check_job(wayback_job):
            if results.completed:
                db = config.kmtools_db
                insert_cur = db.cursor()
                query = f"UPDATE {self.action_table} SET (wayback_url, wayback_timestamp, wayback_details) = (?, ?, ?) WHERE wayback_url = ?"
                values = [
                    results.wayback_url,
                    int(results.timestamp),
                    json.dumps(results.details),
                    wayback_job,
                ]
                config.logger.debug(f"With {query=}, inserting {values=}")
                insert_cur.execute(query, values)
                db.commit()
                return f"{results.original_url} saved as {results.wayback_url}"
            else:
                return f"{results.original_url} not completed ({wayback_job})"
        else:
            return f"No response from Wayback for {wayback_job}"

    def check_job(self, wayback_job=None):
        """Check status of Wayback archive job

        :param job_id: Wayback Machine job id

        :returns Collection with members:
            - completed: bool, True if job is successful
            - in_progress: bool, True if job is in progress
            - status: str, Status value returned by Wayback
            - job_id: str, Wayback Job ID UUID
            - original_url: str, Original URL being saved
            - wayback_url: str, URL of page as saved in Wayback
            - timestamp: int, Timestamp in yyyymmddhhmmss form
            - complete status dictionary
        """

        if not wayback_job or len(wayback_job) == 0:
            return None

        wayback_headers = {
            "Accept": "application/json",
        }
        wayback_endpoint = f"https://web.archive.org/save/status/{wayback_job}"
        config.logger.debug(
            f"Calling endpoint {wayback_endpoint},  {wayback_headers=} (plus auth)"
        )
        wayback_headers[
            "Authorization"
        ] = f"LOW {config.settings.wayback.access_key}:{config.settings.wayback.secret_key}"

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
        if config.dry_run:  # pylint: disable=R1720
            config.logger.info(f"Would have checked status of: {wayback_endpoint}")
            results = Wayback(
                False,  # completed
                False,  # in_progress
                "dry-run",  # status
                wayback_job,  # job_id
                None,  # original_url
                None,  # wayback_url
                None,  # timestamp
                {"status": "dry-run"},
            )
            return results

        r = requests.get(wayback_endpoint, headers=wayback_headers)
        config.logger.debug(f"Returned status {r.status_code}, '{r.text}'")
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
            config.logger.info(f"Job {wayback_job} is {wayback_status}")
            results = Wayback(
                wayback_status == "success",  # completed
                wayback_status == "pending",  # in_progress
                wayback_status,  # status
                wayback_job,  # wayback_job
                wayback_original_url,  # original_url
                wayback_url,  # wayback_url
                wayback_timestamp,  # timestamp
                wayback_details,
            )
            return results

        config.logger.warning(
            f"Couldn't check status of {wayback_job} ({r.status_code}): {r.text}"
        )
        raise exceptions.WaybackError(r.status_code, r.text)

    def process_new(self, origin: Origin) -> None:
        """Process entries that have not yet been processed by this action.

        :param origin: Instance of class Origin that we are processing

        :return: None
        """

        Action.process_new(
            self,
            action_table=self.action_table,
            origin=origin,
            url_action=self.url_action,
        )


wayback_action = Wayback()
config.actions.append(wayback_action)


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
