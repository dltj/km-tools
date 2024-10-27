"""Archive at Wayback"""

import collections
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime

import requests

from kmtools import exceptions
from kmtools.action import Action
from kmtools.source import Origin, Resource, WebResource
from kmtools.util.config import config

logger = logging.getLogger(__name__)


@dataclass
class WaybackRecord:
    url: str
    wayback_url: str
    origin: str
    timestamp_int: int
    timestamp: datetime = field(init=False)

    def __post_init__(self):
        self.timestamp = datetime.fromtimestamp(self.timestamp_int)


class Wayback(Action):

    attributes_supplied = ("wayback_url", "wayback_timestamp", "wayback_details")
    action_table = "action_wayback"

    def url_action(self, source: WebResource):
        """Archive at Wayback

        :param source (WebResource): instance of a web resource

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
        logger.debug(
            "Calling %s, headers=%s (plus auth), %s",
            wayback_endpoint,
            wayback_headers,
            wayback_body,
        )
        wayback_headers["Authorization"] = (
            f"LOW {config.settings.wayback.access_key}:{config.settings.wayback.secret_key}"
        )

        if config.dry_run:  # pylint: disable=R1720
            logger.info("Would have archived: %s", source.uri)
            return

        try:
            r = requests.post(
                wayback_endpoint, headers=wayback_headers, data=wayback_body
            )
        except requests.exceptions.ConnectionError as ex:
            logger.warning("Could not connect to Archive: %s", str(ex))
            return None
        logger.debug("Wayback returned status %s, '%s'", r.status_code, r.text)
        if r.status_code != 200:
            logger.error(
                "Couldn't save url %s (%s): %s", source.uri, r.status_code, r.text
            )
            return None
        try:
            wayback_response = r.json()
        except requests.exceptions.JSONDecodeError:
            logger.error("JSON not returned; wayback response body: '%s'", r.content)
            return None
        if "status" in wayback_response and wayback_response["status"] == "error":
            logger.error(
                "Wayback returned error status; wayback response body: '%s'", r.content
            )
            return None
        if "job_id" not in wayback_response:
            logger.error(
                "Wayback job_id not returned; wayback response body: '%s'", r.content
            )
            return None
        wayback_job = wayback_response["job_id"]
        if "message" in wayback_response:
            logger.warning("Wayback said: %s", wayback_response["message"])
        logger.info("Successfully added %s to Wayback", source.uri)
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
            logger.info("Checking status of %s", row["url"])
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
                logger.debug("With query=%s, inserting values=%s", query, values)
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
        logger.debug(
            "Calling endpoint %s, headers=%s (plus auth)",
            wayback_endpoint,
            wayback_headers,
        )
        wayback_headers["Authorization"] = (
            f"LOW {config.settings.wayback.access_key}:{config.settings.wayback.secret_key}"
        )

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
            logger.info("Would have checked status of: %s", wayback_endpoint)
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
        logger.debug("Returned status %s, '%s'", r.status_code, r.text)
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
            logger.info("Job %s is %s", wayback_job, wayback_status)
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

        logger.warning(
            "Couldn't check status of %s (%s): %s", wayback_job, r.status_code, r.text
        )
        return None

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

    def find_entry(self, url: str) -> WaybackRecord:
        """Returns a dataclass for a record in the Wayback database

        Args:
            url (str): url to search

        Raises:
            exceptions.MoreThanOneError: raised when there is more than one entry in the table
            exceptions.ResourceNotFoundError: raised when the url could not be found

        Returns:
            WaybackRecord: dataclass of database record
        """
        db = config.kmtools_db
        search_cur = db.cursor()
        query = f"SELECT * FROM {self.action_table} WHERE url=:url"
        search_cur.execute(query, [url])
        row = search_cur.fetchone()
        if row:
            wayback_record = WaybackRecord(
                url=url,
                wayback_url=row["wayback_url"],
                origin=row["origin"],
                timestamp_int=int(row["timestamp"]),
            )
            if search_cur.fetchone():
                raise exceptions.MoreThanOneError(url)
        else:
            raise exceptions.ResourceNotFoundError(url)
        return wayback_record

    def find_stalled(self) -> list[WaybackRecord]:
        """Searches the database for stalled Wayback jobs

        Returns:
            list(WaybackRecord): list of database records
        """
        db = config.kmtools_db
        search_cur = db.cursor()
        query = f"SELECT * FROM {self.action_table} WHERE wayback_url LIKE 'spn%'"
        search_cur.execute(query)

        stalled_rows = list()
        for row in search_cur:
            wayback_record = WaybackRecord(
                url=row["url"],
                wayback_url=row["wayback_url"],
                origin=row["origin"],
                timestamp_int=int(row["timestamp"]),
            )
            stalled_rows.append(wayback_record)

        return stalled_rows


wayback_action = Wayback()
config.actions.append(wayback_action)
