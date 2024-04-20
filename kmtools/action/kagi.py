"""Use Kagi APIs to retrieve information"""
import logging

import requests

from kmtools.action import Action
from kmtools.exceptions import SummarizeError
from kmtools.util.config import config

logger = logging.getLogger(__name__)


class Kagi(Action):
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
            f"Calling Kagi Summarize with {kagi_params} and headers {kagi_headers} plus auth"
        )
        kagi_headers["Authorization"] = f"Bot {config.settings.kagi.api_token}"
        r = requests.get(
            "https://kagi.com/api/v0/summarize",
            headers=kagi_headers,
            params=kagi_params,
        )
        logger.debug(f"Kagi returned {r.content}")
        r.raise_for_status()
        try:
            response_json = r.json()
            if "error" in response_json:
                raise RuntimeError(f"Kagi returned {response_json['error'][0]['msg']}")
            if "data" not in response_json or "output" not in response_json["data"]:
                raise ValueError("Data->Output not found")
        except requests.exceptions.JSONDecodeError as ex:
            raise SummarizeError(r.content) from ex

        return response_json["data"]["output"]


kagi_action = Kagi()
