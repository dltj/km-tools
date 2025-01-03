"""Call summarization routines."""

import click

from kmtools.action import kagi_action, summarize_action


@click.command(name="summarize")
@click.option(
    "-q", "--quiet", is_flag=True, default=False, help="Output just the summary"
)
@click.option("-k", "--kagi", is_flag=True, default=False, help="Get summary from Kagi")
@click.option("--traf/--no-traf", default=True, help="Process text with Trafilatura")
@click.argument("url")
@click.pass_obj
def summarize_command(_, url, quiet, kagi, traf) -> None:
    """Output a summarization of the specified URL

    :param details: Context object
    :param url: URL to summarize
    """
    if url:
        if traf:
            derived_date, summarization = summarize_action.get_summary(url)
        else:
            derived_date = None
        if kagi:
            summarization = kagi_action.get_summary(url)
        if not quiet:
            click.echo(
                f"The webpage at {url} was published on {derived_date}. It can be summarized as follows\n"
            )
        click.echo(summarization)
    else:
        click.echo("No URL submitted.")
