import logging

import requests
from sqlalchemy.orm import Session

from kmtools.action.action_base import ActionBase
from kmtools.exceptions import ActionError, ActionSkip
from kmtools.models import ActionKagi, WebResource
from kmtools.util.config import config

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SummarizeWithKagiAction(ActionBase):
    """Summarize a resource with Kagi"""

    action_name = "KagiAction"

    @staticmethod
    def _get_summary(url_to_summarize: str) -> str:
        """Call the Kagi summarize API to retrieve summary

        :param origin_url: URL to the document being summarized

        :raises SummarizeError: Problem with the Kagi API

        :return: Summary paragraph as returned by Kagi
        """
        kagi_params = {"url": url_to_summarize}
        kagi_headers = {"Accept": "application/json"}

        logger.debug(
            "Calling Kagi Summarize with %s and headers %s plus auth",
            kagi_params,
            kagi_headers,
        )
        kagi_headers["Authorization"] = f"Bot {config.settings.kagi.api_token}"
        try:
            r = requests.get(
                "https://kagi.com/api/v0/summarize",
                headers=kagi_headers,
                params=kagi_params,
                timeout=60,
            )
            logger.debug("Kagi returned code %s with %s", r.status_code, r.content)
            response_json = r.json()
        except requests.HTTPError as ex:
            raise ActionSkip(r.content) from ex
        except requests.exceptions.JSONDecodeError as ex:
            raise ActionSkip(r.content) from ex

        if "error" in response_json:
            raise ActionError(f"Kagi returned {response_json['error'][0]['msg']}")
        if not response_json.get("data", {}).get("output"):
            raise ActionError("Data->Output not found in JSON response")

        return response_json["data"]["output"]

    def process(self, session: Session, resource: WebResource) -> None:
        """Get a resource summary from Kagi

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to post to Kagi results in an error
        """

        kagi_action: ActionKagi = ActionKagi(resource=resource)
        kagi_summary = SummarizeWithKagiAction._get_summary(resource.url)

        kagi_action.kagi_summary = kagi_summary
        session.add(kagi_action)
        # Note: Not committing the session here because the process_status object nees a status
        return None


def main():
    # database.Base.metadata.create_all(database.engine)
    # with Session(database.engine) as session:
    #     pinb: Pinboard = Pinboard(
    #         hash="hashblah", href="hrefbalh", time="tieblah", shared=1, toread=1
    #     )
    #     session.add(pinb)
    #     session.commit()

    actions = [
        SummarizeWithKagiAction(),
        # SaveToWaybackAction(),
        # PostToMastodonAction(),
    ]

    for action in actions:
        action.run()


if __name__ == "__main__":
    main()
