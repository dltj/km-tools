import re
from pathlib import Path

import yaml

from kmtools.obsidian.sections import FieldSection, Section
from kmtools.util.config import get_config

HEADER_SENTINEL = "_header"
SECTION_HEADING_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)


class ObsidianPageBase:
    # Subclasses should override to list headings that should be FieldSections
    FIELD_SECTION_HEADINGS: set[str] = set()

    config = get_config()
    DAILY_NOTES: Path = Path(
        config.obsidian.db_directory, config.obsidian.daily_directory
    )

    SOURCES: Path = Path(config.obsidian.db_directory, config.obsidian.source_directory)

    def __init__(self, file_name: str) -> None:
        self.file_name = file_name
        self.frontmatter: dict[str, str] = {}
        self.sections: list[Section] = []

        class_name = self.__class__.__name__
        config = get_config()
        if class_name == "ObsidianDailyPage":
            self._subdirectory = self.DAILY_NOTES
            self._template_file = "Header — Daily.md"
        elif class_name == "ObsidianSourcePage":
            self._subdirectory = self.SOURCES
            self._template_file = "Header — Source.md"
        else:
            raise ValueError(f"Directory configuration not found for {class_name}")
        self.filepath = Path(
            config.obsidian.db_directory, self._subdirectory, self.file_name
        )

        self._read_file()

    def _parse_sections(self, content: str):
        """Splits self.content into a list of Sections.

        The block before the first ## heading becomes a FieldSection with
        heading=None (the _header sentinel). Subsequent sections become
        FieldSection if their heading is in FIELD_SECTION_HEADINGS, otherwise
        a plain Section.
        """
        self.sections = []
        matches = list(SECTION_HEADING_PATTERN.finditer(content))

        def make_section(heading: str | None, content: str) -> Section:
            content = content.strip()
            if heading is None or heading in self.FIELD_SECTION_HEADINGS:
                return FieldSection(heading=heading, content=content)
            return Section(heading=heading, content=content)

        if not matches:
            # Entire content is a single header block
            self.sections.append(make_section(None, content))
            return

        # Block before the first heading
        pre_content = content[: matches[0].start()]
        self.sections.append(make_section(None, pre_content))

        # Each heading and the content that follows it
        for i, match in enumerate(matches):
            heading = match.group(1)
            content_start = match.end()
            content_end = (
                matches[i + 1].start() if i + 1 < len(matches) else len(content)
            )
            section_content = content[content_start:content_end]
            self.sections.append(make_section(heading, section_content))

    def get_section(self, heading: str | None) -> Section | None:
        """Returns the section with the given heading, or None if not found.

        Pass None to retrieve the _header sentinel block.
        """
        for section in self.sections:
            if section.heading == heading:
                return section
        return None

    def set_section(self, heading: str | None, content: str):
        """Replaces the content of an existing section, or appends a new one."""
        for section in self.sections:
            if section.heading == heading:
                section.content = content
                if isinstance(section, FieldSection):
                    section._parse_fields()
                return
        # Section not found — append it
        if heading is None or heading in self.FIELD_SECTION_HEADINGS:
            self.sections.append(FieldSection(heading=heading, content=content))
        else:
            self.sections.append(Section(heading=heading, content=content))

    def put_section(self, section: Section):
        """Replaces a Section by matching on section.heading, or appends if not found."""
        for i, existing in enumerate(self.sections):
            if existing.heading == section.heading:
                self.sections[i] = section
                return
        self.sections.append(section)

    def _reassemble_content(self) -> str:
        """Rebuilds self.content from self.sections for saving."""
        parts = []
        for section in self.sections:
            if section.heading is None:
                parts.append(section.get_content())
            else:
                parts.append(f"## {section.heading}\n{section.get_content()}")
        return "\n\n".join(parts)

    def _read_file(self):
        """Reads the file and parses the YAML frontmatter and the Markdown content."""
        if not self.filepath.exists() or self.filepath.stat().st_size == 0:
            text = self.read_template()
        else:
            with self.filepath.open("r", encoding="utf-8") as f:
                text = f.read()

        # Split the file into frontmatter and content
        content = ""
        if text.startswith("---"):
            _, frontmatter_text, content = text.split("---", 2)
            self.frontmatter = yaml.safe_load(frontmatter_text.strip()) or {}

        if content:
            self._parse_sections(content=content)

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
            f.write(f"---\n{frontmatter_text}---\n{self._reassemble_content()}")

    # def parse_markdown(self):
    #     """Parses the markdown content into HTML or another format."""
    #     return markdown.markdown(self.content)

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
        config = get_config()
        templatepath = Path(
            config.obsidian.db_directory,
            config.obsidian.template_directory,
            self._template_file,
        )
        with templatepath.open("r", encoding="utf-8") as f:
            text = f.read()

        return text
