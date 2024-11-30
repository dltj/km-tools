import json
import logging
from typing import Tuple

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from kmtools.action.action_base import ActionBase
from kmtools.exceptions import ActionError, ActionSkip
from kmtools.models import ActionWayback, WebResource
from kmtools.util.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _make_wayback_request(method: str, url: str, data: dict = None) -> dict:
    wayback_headers = {
        "Accept": "application/json",
    }
    logger.debug(
        "Calling %s %s, headers=%s (plus auth), %s",
        method.upper(),
        url,
        wayback_headers,
        data,
    )

    if config.dry_run:  # pylint: disable=R1720
        logger.info("Would have archived: %s", url)
        return

    wayback_headers["Authorization"] = (
        f"LOW {config.settings.wayback.access_key}:{config.settings.wayback.secret_key}"
    )

    try:
        if method.lower() == "post":
            response = requests.post(
                url, headers=wayback_headers, data=data, timeout=10
            )
        elif method.lower() == "get":
            response = requests.get(url, headers=wayback_headers, timeout=10)
        else:
            raise ActionError("Unsupported HTTP method")
    except requests.exceptions.ReadTimeout as ex:
        logger.warning("Timeout connecting to Archive: %s", str(ex))
        raise ActionSkip("Wayback API connection timeout") from ex
    except requests.exceptions.ConnectionError as ex:
        logger.warning("Could not connect to Archive: %s", str(ex))
        raise ActionSkip("No connection to Wayback API") from ex

    logger.debug(
        "Wayback returned status %s, '%s'", response.status_code, response.text
    )
    if response.status_code != 200:
        logger.error(
            "Couldn't save url %s (%s): %s", url, response.status_code, response.text
        )
        raise ActionSkip("Non-200 response code from Wayback")

    try:
        wayback_response = response.json()
    except requests.exceptions.JSONDecodeError as ex:
        logger.error("JSON not returned; wayback response body: '%s'", response.content)
        raise ActionSkip("Non-JSON body from Wayback") from ex

    if wayback_response.get("status") == "error":
        logger.error(
            "Wayback returned error status; wayback response body: '%s'",
            response.content,
        )
        raise ActionError("Wayback returned error")

    if "job_id" not in wayback_response:
        logger.error(
            "Wayback job_id not returned; wayback response body: '%s'", response.content
        )
        raise ActionSkip("job_id not found in response from Wayback")
    return wayback_response


class SaveToWaybackAction(ActionBase):
    """Save a URL to the WayBack machine

    This class is the first of a two-stage process. The process() method
    requests that the Wayback machine store a page in its system. What
    is returned from Wayback is a "spn" (Save Page Now) identifier that
    is later used to retrieve information about the status of the save
    request.
    """

    action_name = "WaybackSaveAction"

    @staticmethod
    def _wayback_save_page_now(url_to_save: str) -> str:
        """Save page to WayBack machine.

        :param resource:  WebResource object

        :returns: Identifier of the Save Page Now request
        """
        ## This conditional effectively skips saving Internet Archive URLs into wayback
        if (
            url_to_save.startswith("https://archive.org/")
            or url_to_save.startswith("https://archive.is/")
            or url_to_save.startswith("https://archive.ph/")
        ):
            return url_to_save

        wayback_body = {
            "url": url_to_save,
            "capture_screenshot": 1,
            "delay_wb_availability": 1,
            "skip_first_archive": 1,
            "email_result": 0,
        }
        wayback_endpoint = "https://web.archive.org/save"

        wayback_response = _make_wayback_request(
            method="post", url=wayback_endpoint, data=wayback_body
        )

        wayback_job = wayback_response["job_id"]
        if "message" in wayback_response:
            logger.warning("Wayback said: %s", wayback_response["message"])
        logger.info("Successfully added %s to Wayback (%s)", url_to_save, wayback_job)
        return wayback_job

    def process(self, session: Session, resource: WebResource) -> None:
        """Save a url in Wayback

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to post to Wayback results in an error
        """

        wayback_action: ActionWayback = ActionWayback(resource=resource)
        spn_identifier = SaveToWaybackAction._wayback_save_page_now(resource.url)

        wayback_action.wayback_url = spn_identifier
        session.add(wayback_action)
        # Note: Not committing the session here because the process_status object needs a status
        return


class ResultsFromWaybackAction(ActionBase):
    """Retrieve results from a Wayback save-page-now request

    This class is the second of a two-stage process. The process() method
    retrieves the status information from the earlier save-page-now request
    (using the `spn` identifier), and if the request has been succesfully
    processed, it saves the results in the database.
    """

    action_name = "WaybackResultsAction"

    @staticmethod
    def _wayback_retrieve_status(spn_identifier) -> Tuple[str, str, str]:
        """Retrieve results of save-page-now request from Wayback

        :param spn_identifier:  Identifier for the save-page-now request

        :returns Tuple:
            - Wayback URL to the saved page
            - Date at which Wayback finished saving the page
            - Details from Wayback about what was stored
        """
        if not spn_identifier:
            return None

        wayback_endpoint = f"https://web.archive.org/save/status/{spn_identifier}"

        wayback_response = _make_wayback_request(method="get", url=wayback_endpoint)

        wayback_job = wayback_response["job_id"]
        if "message" in wayback_response:
            logger.warning("Wayback said: %s", wayback_response["message"])

        wayback_status = wayback_response["status"]
        wayback_original_url = wayback_response.get("original_url")
        wayback_timestamp = wayback_response.get("timestamp")
        wayback_url = (
            f"https://web.archive.org/{wayback_timestamp}/{wayback_original_url}"
            if wayback_timestamp and wayback_original_url
            else None
        )

        if wayback_url and wayback_timestamp:
            logger.info(
                "Successfully added %s to Wayback (%s); status: %s",
                wayback_original_url,
                wayback_job,
                wayback_status,
            )
            return wayback_url, wayback_timestamp, wayback_response

        logger.warning(
            "Couldn't check status of %s. wayback timestamp (%s) or wayback original_url (%s) missing from response.",
            wayback_job,
            wayback_timestamp,
            wayback_url,
        )
        raise ActionError("Malformed Wayback Response")

    def process(self, session: Session, resource: WebResource) -> None:
        """Retrieve results from a Wayback save-page-now request

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        Returns a None response when the Save-Page-Now action is complete. This
        could be because we get a positive response from the Wayback endpoint,
        or it could be because the ActionWayback.wayback.url value has been
        edited to remove the SPN identifier.

        :raises:
            - ActionException: when the SPN request isn't finished
        """

        ## If there is no process_status record yet, then we have nothing to check. Tell
        ## the action runner to skip this resource.
        stmnt = select(ActionWayback).where(ActionWayback.resource_id == resource.id)
        wayback_action = session.execute(stmnt).scalars().first()
        if not wayback_action:
            raise ActionSkip("No ActionWayback object for WebResource yet")

        spn_identifier: str = wayback_action.wayback_url

        # Return if wayback_url doesn't start with 'spn'
        if not spn_identifier or not spn_identifier.startswith("spn"):
            return
        wayback_url, wayback_timestamp, wayback_details = self._wayback_retrieve_status(
            spn_identifier
        )

        wayback_action.wayback_url = wayback_url
        wayback_action.wayback_timestamp = wayback_timestamp
        wayback_action.wayback_details = json.dumps(wayback_details)
        # Note: Not committing the session here because the process_status object nees a status
        return


def main():
    # database.Base.metadata.create_all(database.engine)
    # with Session(database.engine) as session:
    #     pinb: Pinboard = Pinboard(
    #         hash="hashblah", href="hrefbalh", time="tieblah", shared=1, toread=1
    #     )
    #     session.add(pinb)
    #     session.commit()

    actions = [
        ResultsFromWaybackAction(),
    ]

    for action in actions:
        action.run()


if __name__ == "__main__":
    main()
