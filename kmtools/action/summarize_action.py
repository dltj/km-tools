import heapq
import logging
import re
from typing import Tuple

import nltk
import trafilatura
from sqlalchemy.orm import Session
from trafilatura.settings import use_config

from kmtools.action.action_base import ActionBase
from kmtools.exceptions import ActionError, SummarizeError
from kmtools.models import ActionSummary, WebResource

logger = logging.getLogger(__name__)


def _get_document(resource_url: str) -> str:
    """Use Trafilatura to get a web resource

    Args:
        resource_url (str): the web resource URL

    Raises:
        SummarizeError: when trafilatura encounters an error

    Returns:
        str: Unicode string of document text
    """
    trafilatura_config = use_config()
    trafilatura_config.set(
        "DEFAULT",
        "USER_AGENTS",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    )
    # Fetch and extract main body of webpage from URL
    downloaded = trafilatura.fetch_url(resource_url, config=trafilatura_config)
    if not downloaded:
        logger.warning("Couldn't fetch content of %s", resource_url)
        raise SummarizeError(f"Couldn't fetch content of {resource_url}")

    return downloaded


def _get_derived_date(resource_url: str, downloaded) -> str:
    metadata: dict = trafilatura.extract_metadata(
        downloaded,
        default_url=resource_url,
        # date_config={"extensive_search": True},
    )
    if metadata and metadata.date:
        derived_date = metadata.date
    else:
        derived_date = "unknown"
    return derived_date


def _get_summarization(resource_url: str, downloaded: str) -> str:
    raw_text = trafilatura.extract(
        downloaded,
        favor_precision=True,
        output_format="txt",
        include_tables=False,
    )
    if raw_text is None:
        logger.info("No summarization from %s", resource_url)
        return None

    # Remove timestamps on lines by themselves
    raw_text = re.sub(r"\n[0-9]+:[0-9]+:[0-9]+\n", " ", raw_text)
    logger.debug("raw_text=%s", raw_text)

    normalized_raw_text = re.sub("[^a-zA-Z']", " ", raw_text)
    normalized_raw_text = re.sub(r"\s+", " ", normalized_raw_text)

    # nltk.download("stopwords")
    # nltk.download("punkt")
    stopwords = nltk.corpus.stopwords.words("english")
    word_frequencies: dict = {}
    for word in nltk.word_tokenize(normalized_raw_text):
        if word not in stopwords:
            if word not in word_frequencies:
                word_frequencies[word] = 1
            else:
                word_frequencies[word] += 1

    maximum_frequncy = max(word_frequencies.values())
    for word in word_frequencies:
        word_frequencies[word] = word_frequencies[word] / maximum_frequncy

    sentence_list = nltk.sent_tokenize(raw_text)
    if len(sentence_list) < 7:
        ## There are less than seven sentences (is this an uncorrected transcript?),
        ## so just return the 50 most popular words
        sorted_word_frequencies = {
            k: v for k, v in sorted(word_frequencies.items(), key=lambda item: item[1])
        }
        summarization = " ".join(list(sorted_word_frequencies.keys())[-50:])
    else:
        sentence_scores = {}
        for sent in sentence_list:
            for word in nltk.word_tokenize(sent.lower()):
                if word in word_frequencies:
                    if len(sent.split(" ")) < 30:
                        if sent not in sentence_scores:
                            sentence_scores[sent] = word_frequencies[word]
                        else:
                            sentence_scores[sent] += word_frequencies[word]
        summary_sentences = heapq.nlargest(7, sentence_scores, key=sentence_scores.get)
        summarization = " ".join(summary_sentences)

    return summarization


def get_summary(resource_url: str) -> Tuple[str, str]:
    try:
        downloaded = _get_document(resource_url)
    except SummarizeError as e:
        raise ActionError(f"Could not process {resource_url}") from e
    derived_date: str = _get_derived_date(resource_url, downloaded)
    summarization: str = _get_summarization(resource_url, downloaded)
    return derived_date, summarization


class SummarizeAction(ActionBase):
    """Summarize a resource"""

    action_name = "SummarizeAction"

    def process(self, session: Session, resource: WebResource) -> None:
        """Get summary and derived date of source.

        :param session: SQLAlchemy session
        :param resource: Instance of class WebResource

        :raises:
            - ActionException: when the attempt to get the summary results in an error
        """

        resource_url: str = resource.url
        derived_date, summarization = get_summary(resource_url)
        summary: ActionSummary = ActionSummary(resource=resource)
        session.add(summary)
        summary.derived_date = derived_date
        summary.summary = summarization
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

    # actions = [
    #     SummarizeAction(),
    #     # SaveToWaybackAction(),
    #     # PostToMastodonAction(),
    # ]

    # for action in actions:
    #     action.run()


if __name__ == "__main__":
    main()
