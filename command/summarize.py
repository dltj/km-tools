"""Call summarization routines."""
import re
import heapq
import click
import trafilatura
import nltk


@click.command(name="summarize")
@click.option(
    "-q", "--quiet", is_flag=True, default=False, help="Output just the summary"
)
@click.argument("url")
@click.pass_obj
def summarize_command(details, url=None, quiet=False):
    """Output a summarization of the specified URL

    :param details: Context object
    :param url: URL to summarize
    """
    if url:
        derived_date, summarization = summarize(details, url)
        if not quiet:
            click.echo(
                f"The webpage at {url} was published on {derived_date}. It can be summarized as follows\n"
            )
        click.echo(summarization)
    else:
        click.echo("No URL submitted.")


def summarize(details, url):
    # Fetch and extract main body of webpage from URL
    downloaded = trafilatura.fetch_url(url)
    metadata = trafilatura.extract_metadata(
        downloaded,
        default_url=url,
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
    details.logger.debug(f"{raw_text=}")

    # Removing special characters and digits
    if raw_text is None:
        details.logger.info(f"No summarization from {url}")
        return None, None

    normalized_raw_text = re.sub("[^a-zA-Z]", " ", raw_text)
    normalized_raw_text = re.sub(r"s+", " ", normalized_raw_text)

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
