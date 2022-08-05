"""Output links that have been robustified."""
import logging
from string import Template

import click
from dateutil import parser
from exceptions import MoreThanOneError
from source import hypothesis, pinboard

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--jekyll",
    "style",
    flag_value="jekyll",
    default=True,
    help="Output in Jekyll 'include html' format (default)",
)
@click.option(
    "--html",
    "style",
    flag_value="html",
    help="Output in HTML <a> anchor format",
)
@click.option(
    "--thursday-threads",
    "style",
    flag_value="tt",
    help="Output in Jekyll 'include thursday-threads' format",
)
@click.argument("url")
@click.pass_obj
def robustify(details, style, url):
    """Output markup for a robust link"""
    logger.debug(f"Searching for {url}")
    try:
        webpage_pinboard = pinboard.find_entry(details, url)
    except MoreThanOneError:
        logger.error(f"More than one pinboard entry found for {url}. Exiting.")
        return

    try:
        webpage_hypothesis = hypothesis.find_entry(details, url)
    except MoreThanOneError:
        logger.error(f"More than one hypothesis page found for {url}. Exiting.")
        return

    if webpage_pinboard and webpage_hypothesis:
        logger.error(f"{url} found in both Pinboard and Hypothesis. Exiting.")
        return

    if not webpage_pinboard and not webpage_hypothesis:
        logger.warning(f"{url} not found in Pinboard and Hypothesis. Exiting.")
        return

    webpage = webpage_pinboard if webpage_pinboard else webpage_hypothesis
    archive_date = parser.parse(webpage.archive_date).strftime("%Y-%m-%d")

    if style == "html":
        robust_template = Template(
            '<a href="$href" data-versionurl="$archive_url" '
            'data-versiondate="$archive_date" title="$title">REPLACE_ME</a>'
        )
    elif style == "tt":
        robust_template = Template(
            """
{% include thursday-threads-quote.html
blockquote=''
href="$href"
versionurl="$archive_url"
versiondate="$archive_date"
anchor="$title"
post=''
%}"""
        )
    else:
        robust_template = Template(
            '{% include robustlink.html href="$href" versionurl="$archive_url" '
            'versiondate="$archive_date" title="$title" anchor="REPLACE_ME" %}',
        )

    robust_string = robust_template.substitute(
        {
            "href": webpage.href,
            "archive_url": webpage.archive_url,
            "archive_date": archive_date,
            "title": webpage.title,
        }
    )

    print(robust_string)
