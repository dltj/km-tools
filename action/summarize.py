"""Get summary of item"""
import heapq
import re
import time

import nltk
import trafilatura
from config import config
from source import Origin, Resource, WebResource

from action import Action


class Summarize(Action):
    attributes_supplied = ["summary", "derived_date"]
    action_table = "action_summary"

    def __init__(self) -> None:
        super().__init__()

    def url_action(self, source: WebResource):
        """
        Store summary and derived date in table

        :param source: Instance of class WebResource

        :returns: None
        """
        derived_date, summary = summarize(source=source)

        config.logger.info(
            f"Successfully summarized {source.uri} as {derived_date} / {summary}"
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
    """

    # Fetch and extract main body of webpage from URL
    downloaded = trafilatura.fetch_url(source.url)
    metadata = trafilatura.extract_metadata(
        downloaded,
        default_url=source.url,
        date_config={"extensive_search": True},
    )
    if metadata and metadata["date"]:
        derived_date = metadata["date"]
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
        config.logger.info(f"No summarization from {source.url}")
        return None, None
    # Remove timestamps on lines by themselves
    raw_text = re.sub(r"\n[0-9]+:[0-9]+:[0-9]+\n", " ", raw_text)
    config.logger.debug(f"{raw_text=}")

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
