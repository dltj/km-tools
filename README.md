# Personal Knowledge Management Tools

`kmtools` is a script with commands that I'm using to save Hypothesis annotations and Pinboard bookmarks to a local database, then create daily Markdown documents reflecting newly created resources.

## Activity Sources

The [sources directory](source/) has two adapters...one for bookmarks stored to [Pinboard](https://pinboard.in/) and another for annotations made to web-accessible HTML/PDF files using [Hypothesis](https://hypothes.is).

## Actions

There are actions for posting to Twitter and Mastodon. There is also an action for saving a web resource to Wayback at the Internet Archive.

## Time-based Commands

There is an 'hourly' command that pulls new content from the activity sources and applies the Twitter, Mastodon, and Wayback actions. For Twitter and Mastodon, the posted text includes the title of the bookmark or annotation, a link to the resource, and—in the case of annotations—a link to the annotated view of the resource.

There is a 'daily' command that runs overnight to create a daily diary page in [Obsidian](https://obsidian.md). The daily diary page is a Markdown document that contains the list of new activity source material from the day before as well as meditation prompts for the morning and evening. The 'daily' command also writes a "Source" file into the Obsidian database for bookmarks/annotations that contain a tag. (In the Obsidian database, bookmark/annotation tags translate to Concept pages.)

## Utility Commands

There is a 'summarize' command that retrieves the web resource and makes a statistical sampling of high-value sentences. The summary is added to the resource's "Source" page.

There is a 'robustify' command that, when given a URL to a bookmark/annotation, creates a [Robust Link](https://robustlinks.mementoweb.org/about/) using the URL to the Wayback archive as the `data-versionurl` HTTP anchor attribute.

## Installation

Use pipenv to create an isolated Python environment with the proper prerequisites

```bash
git clone https://github.com/dltj/kmtools
cd kmtools
pipenv install
pipx install --editable .
```

## Usage

```bash
kmtools [--verbose|--debug] hourly
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
