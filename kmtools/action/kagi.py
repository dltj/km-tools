"""Use Kagi APIs to retrieve information"""

import logging

import requests

from kmtools.action import Action
from kmtools.exceptions import SummarizeError
from kmtools.source import Origin, Resource, WebResource
from kmtools.util.config import config

logger = logging.getLogger(__name__)


class Kagi(Action):
    """Use the Kagi AI summarizer"""

    attributes_supplied = ["kagi_summary"]
    action_table = "action_kagi"

    def url_action(self, source: WebResource) -> None:
        """Store summary from the Kagi AI Summarizer in table

        :param source: Instance of class WebResource
        :type source: WebResource
        :returns: None
        """
        try:
            summary = self.retrieve_summary(source.uri)
        except (SummarizeError, ValueError) as ex:
            logger.error("Kagi summarizer exception %s for %s", ex, source.uri)
            return
        logger.info("Successfully summarized %s as %s", source.uri, summary)

        Action._save_attributes(self, source, self.attributes_supplied, [summary])
        return

    def attribute_read(self, source: Resource, name: str) -> str:
        return Action._attribute_read(self, name, self.action_table, source.uri)

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

    def retrieve_summary(self, origin_url: str) -> str:
        """Call the Kagi summarize API to retrieve summary

        :param origin_url: URL to the document being summarized
        :type origin_url: str
        :raises SummarizeError: Problem with the Kagi API
        :return: Summary paragraph as returned by Kagi
        :rtype: str
        """
        kagi_params = {"url": origin_url}
        kagi_headers = {"Accept": "application/json"}

        logger.debug(
            "Calling Kagi Summarize with %s and headers %s plus auth",
            kagi_params,
            kagi_headers,
        )
        kagi_headers["Authorization"] = f"Bot {config.settings.kagi.api_token}"
        r = requests.get(
            "https://kagi.com/api/v0/summarize",
            headers=kagi_headers,
            params=kagi_params,
        )
        logger.debug("Kagi returned %s", r.content)
        try:
            r.raise_for_status()
            response_json = r.json()
            if "error" in response_json:
                raise SummarizeError(
                    f"Kagi returned {response_json['error'][0]['msg']}"
                )
            if "data" not in response_json or "output" not in response_json["data"]:
                raise ValueError("Data->Output not found")
        except requests.HTTPError as ex:
            raise SummarizeError(r.content) from ex
        except requests.exceptions.JSONDecodeError as ex:
            raise SummarizeError(r.content) from ex

        return response_json["data"]["output"]


kagi_action = Kagi()
config.actions.append(kagi_action)
