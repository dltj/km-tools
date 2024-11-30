from pathlib import Path

import yaml

from kmtools.util.config import config


class ObsidianPageBase:

    def __init__(self, file_name: str) -> None:
        self.file_name = file_name
        self.frontmatter = {}
        self.content = ""

        class_name = self.__class__.__name__
        if class_name == "ObsidianDailyPage":
            self._subdirectory = config.settings.obsidian.daily_directory
            self._template_file = "Header — Daily.md"
        elif class_name == "ObsidianSourcePage":
            self._subdirectory = config.settings.obsidian.source_directory
            self._template_file = "Header — Source.md"
        else:
            raise ValueError(f"Directory configuration not found for {class_name}")
        self.filepath = Path(
            config.settings.obsidian.db_directory, self._subdirectory, self.file_name
        )

        self._read_file()

    def _read_file(self):
        """Reads the file and parses the YAML frontmatter and the Markdown content."""
        if not self.filepath.exists() or self.filepath.stat().st_size == 0:
            text = self.read_template()
        else:
            with self.filepath.open("r", encoding="utf-8") as f:
                text = f.read()

        # Split the file into frontmatter and content
        if text.startswith("---"):
            _, frontmatter_text, self.content = text.split("---", 2)
            self.frontmatter = yaml.safe_load(frontmatter_text.strip()) or {}

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context and save the changes to the file."""
        self.save()

    def save(self):
        """Writes the current state back to the markdown file."""
        with self.filepath.open("w", encoding="utf-8") as f:
            frontmatter_text = yaml.safe_dump(self.frontmatter, sort_keys=False)
            f.write(f"---\n{frontmatter_text}---\n{self.content}")

    # def parse_markdown(self):
    #     """Parses the markdown content into HTML or another format."""
    #     return markdown.markdown(self.content)

    def modify_content(self, new_content: str):
        """Modifies the markdown content."""
        self.content = new_content

    def read_template(self):
        """Reads the content of a template file from the specified template directory.

        This method constructs a file path using the configuration settings for the
        directory location and the template file name. It opens the template file in
        read mode with UTF-8 encoding, reads its content, and returns it as a string.

        Returns:
            str: The content of the template file as a string.

        Raises:
            FileNotFoundError: If the template file does not exist.
            IOError: If the file cannot be read due to an I/O error.

        Example:
            text = self.read_template()
            print(text)
        """
        templatepath = Path(
            config.settings.obsidian.db_directory,
            config.settings.obsidian.template_directory,
            self._template_file,
        )
        with templatepath.open("r", encoding="utf-8") as f:
            text = f.read()

        return text
