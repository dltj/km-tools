"""Get summary of item"""

import heapq
import logging
import re

import nltk
import trafilatura
from trafilatura.settings import use_config

from kmtools.action import Action
from kmtools.exceptions import SummarizeError
from kmtools.source import Origin, Resource, WebResource
from kmtools.util.config import config

logger = logging.getLogger(__name__)


class Summarize(Action):
    """Summarize a document using Trafilatura"""

    attributes_supplied = ["summary", "derived_date"]
    action_table = "action_summary"

    def url_action(self, source: WebResource):
        """
        Store summary and derived date in table

        :param source: Instance of class WebResource

        :returns: None
        """
        try:
            derived_date, summary = summarize(source=source)
        except SummarizeError:
            return

        logger.info(
            "Successfully summarized %s as %s / %s", source.uri, derived_date, summary
        )
        Action._save_attributes(
            self, source, self.attributes_supplied, [summary, derived_date]
        )
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


summarize_action = Summarize()
config.actions.append(summarize_action)


def summarize(source: WebResource = None):
    """Get summary and derived date of source.

    :param source: Instance of class WebResource

    :returns:
        - derived_date: date as parsed by the Trafilatura library (string)
        - summary: 7 highest scoring sentences or 50 most common words

    :raises:
        - SummarizeException: when Trafilatura returns an error.
    """

    trafilatura_config = use_config()
    trafilatura_config.set(
        "DEFAULT",
        "USER_AGENTS",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    )
    # Fetch and extract main body of webpage from URL
    downloaded = trafilatura.fetch_url(source.url, config=trafilatura_config)
    if not downloaded:
        logger.warning("Couldn't fetch content of %s", source.url)
        raise SummarizeError(f"Couldn't fetch content of {source.url}")

    metadata = trafilatura.extract_metadata(
        downloaded,
        default_url=source.url,
        date_config={"extensive_search": True},
    )
    if metadata and metadata.date:
        derived_date = metadata.date
    else:
        derived_date = "unknown"

    raw_text = trafilatura.extract(
        downloaded,
        favor_precision=True,
        output_format="txt",
        include_tables=False,
    )

    # Removing special characters and digits
    if raw_text is None:
        logger.info("No summarization from %s", source.url)
        return None, None
    # Remove timestamps on lines by themselves
    raw_text = re.sub(r"\n[0-9]+:[0-9]+:[0-9]+\n", " ", raw_text)
    logger.debug("raw_text=%s", raw_text)

    normalized_raw_text = re.sub("[^a-zA-Z']", " ", raw_text)
    normalized_raw_text = re.sub(r"\s+", " ", normalized_raw_text)

    # nltk.download("stopwords")
    # nltk.download("punkt")
    stopwords = nltk.corpus.stopwords.words("english")
    word_frequencies = {}
    for word in nltk.word_tokenize(normalized_raw_text):
        if word not in stopwords:
            if word not in word_frequencies.keys():
                word_frequencies[word] = 1
            else:
                word_frequencies[word] += 1

    maximum_frequncy = max(word_frequencies.values())
    for word in word_frequencies.keys():
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
                if word in word_frequencies.keys():
                    if len(sent.split(" ")) < 30:
                        if sent not in sentence_scores.keys():
                            sentence_scores[sent] = word_frequencies[word]
                        else:
                            sentence_scores[sent] += word_frequencies[word]
        summary_sentences = heapq.nlargest(7, sentence_scores, key=sentence_scores.get)
        summarization = " ".join(summary_sentences)

    return derived_date, summarization
