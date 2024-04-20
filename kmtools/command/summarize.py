"""Call summarization routines."""

import click

from kmtools.action import summarize
from kmtools.action.kagi import kagi_action
from kmtools.source import WebResource


@click.command(name="summarize")
@click.option(
    "-q", "--quiet", is_flag=True, default=False, help="Output just the summary"
)
@click.option("-k", "--kagi", is_flag=True, default=False, help="Get summary from Kagi")
@click.argument("url")
@click.pass_obj
def summarize_command(_, url=None, quiet=False, kagi=False) -> None:
    """Output a summarization of the specified URL

    :param details: Context object
    :param url: URL to summarize
    """
    if url:
        source = WebResource(url)
        derived_date, summarization = summarize.summarize(source)
        if kagi:
            summarization = kagi_action.retrieve_summary(url)
        if not quiet:
            click.echo(
                f"The webpage at {url} was published on {derived_date}. It can be summarized as follows\n"
            )
        click.echo(summarization)
    else:
        click.echo("No URL submitted.")
