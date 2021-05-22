# Personal Knowledge Management Tools

`kmtools` is a script with commands that I'm using to save Hypothesis annotations and Pinboard bookmarks to a local database, then create daily Markdown documents reflecting newly created resources.

## Installation

Use pipenv to create an isolated Python environment with the proper prerequisites

```bash
git clone https://github.com/dltj/kmtools
cd kmtools
pipenv install
```

## Usage

```bash
pipenv run kmtools [--verbose|--debug] hourly
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[MIT](https://choosealicense.com/licenses/mit/)