import logging
import re
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

from kmtools.obsidian.page_base import ObsidianPageBase

from .sections import FieldSection

logger = logging.getLogger(__name__)


class ObsidianDailyPage(ObsidianPageBase):
    FIELD_SECTION_HEADINGS = {"End-of-day"}

    SEC_PREAMBLE = None
    SEC_TAGS = "Tags for Today"
    SEC_MORNING = "Morning Notes"
    SEC_READINGS = "Yesterday's readings"
    SEC_DAILY = "Daily notes"
    SEC_EOD = "End-of-day"

    DATE_OFFSETS = [
        ("-72 month", "Six years ago"),
        ("-60 month", "Five years ago"),
        ("-48 month", "Four years ago"),
        ("-36 month", "Three years ago"),
        ("-24 month", "Two years ago"),
        ("-18 month", "18 months ago"),
        ("-12 month", "Last year"),
        ("-6 month", "Six months ago"),
        ("-3 month", "Three months ago"),
        ("-1 month", "Last month"),
        ("-14 day", "Two weeks ago"),
        ("-7 day", "Last week"),
        ("-1 day", "Yesterday"),
        ("1 day", "Tomorrow"),
    ]

    def __init__(self, file_name: str) -> None:
        ## First check if `file_name` (minus the `.md` extension) is a parsable YYYY-MM-DD
        try:
            self._dateobj: date = datetime.strptime(
                file_name.removesuffix(".md"), "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValueError(f"`{file_name}` is not a parsable YYYY-MM-DD date.")

        super().__init__(file_name)

    def update_template_dates(self):
        """Updates date-related fields and the Tags query line in the header section."""

        def parse_timedelta(time_str: str) -> relativedelta:
            value_str, unit = time_str.split()
            value = int(value_str)
            if "day" in unit:
                return relativedelta(days=value)
            elif "month" in unit:
                return relativedelta(months=value)
            raise ValueError("Unsupported unit")

        def get_date_line(daily_note_date: date, offset: str) -> str | None:
            target_date = daily_note_date + parse_timedelta(offset)
            target_date_file = (
                self.DAILY_NOTES / f"{target_date.strftime('%Y-%m-%d')}.md"
            )
            if target_date_file.exists():
                return target_date.strftime("%Y-%m-%d")
            return None

        preamble = FieldSection(heading=None, content="")
        preamble.fields["Weekday"] = self._dateobj.strftime("%A")
        for offset, label in self.DATE_OFFSETS:
            if date_file := get_date_line(self._dateobj, offset):
                preamble.fields[label] = f"[[{date_file}]]"
        self.put_section(preamble)

        if date.today() - self._dateobj > timedelta(days=5):
            return

        # Update the Tags for Today section
        date_today = self._dateobj.strftime("%d-%b")
        tag_dataview = "\n".join(["```dataview", f"LIST FROM #{date_today}", "```"])
        self.set_section(self.SEC_TAGS, tag_dataview)

    @property
    def readings(self) -> list[str]:
        """Returns the Yesterday's readings section as a list of strings."""
        section = self.get_section(self.SEC_READINGS)
        if not section or not section.content:
            return []
        return [
            line.lstrip("- ").strip()
            for line in section.content.splitlines()
            if line.startswith("- ")
        ]

    @readings.setter
    def readings(self, items: list[str]):
        """Sets the Yesterday's readings section from a list of strings."""
        content = "\n".join(f"- {item}" for item in items)
        self.set_section(self.SEC_READINGS, content)

    @staticmethod
    def _is_content_empty(text: str) -> bool:
        """Returns True if text contains no meaningful content.

        Strips lines that are only dashes, list markers, numbers, and whitespace.
        """
        for line in text.splitlines():
            cleaned = (
                line.strip()
                .lstrip("0123456789")
                .lstrip(".")
                .strip()
                .lstrip("-")
                .strip()
            )
            if cleaned:
                return False
        return True

    def cleanup_empty_sections(self):
        """Removes empty headings and sections from the page."""
        self._cleanup_subsections()
        self._cleanup_top_sections()

    def _cleanup_subsections(self):
        """Removes empty ### headings from within eash section's content."""
        SUB_HEADING_PATTERN = re.compile(r"^### .+$", re.MULTILINE)
        for section in self.sections:
            if section.heading in [None, self.SEC_TAGS]:
                continue  # Preamble or "Tags for Today"
            content = section.get_content()

            # Find all ### headings
            sub_matches = list(SUB_HEADING_PATTERN.finditer(content))
            if not sub_matches:
                continue

            kept_parts = []
            for i, match in enumerate(sub_matches):
                sub_content_start = match.end()
                sub_content_end = (
                    sub_matches[i + 1].start()
                    if i + 1 < len(sub_matches)
                    else len(content)
                )
                sub_content = content[sub_content_start:sub_content_end].strip()
                if not self._is_content_empty(sub_content):
                    kept_parts.append(f"{match.group()}\n{sub_content}")

            # Preserve any content before the first ### heading
            pre_content = content[: sub_matches[0].start()].strip()
            section.content = "\n\n".join(filter(None, [pre_content] + kept_parts))

    def _cleanup_top_sections(self):
        """Removes any empty ## sections and empty fields from FieldSections."""
        kept_sections = []
        for section in self.sections:
            if section.heading in [None, self.SEC_TAGS]:
                # Skip the preamble and tags-for-today; they can be regenerated
                continue

            if isinstance(section, FieldSection):
                section.fields = {k: v for k, v in section.fields.items() if v.strip()}
                if section.fields:
                    kept_sections.append(section)
                continue

            if section.heading == self.SEC_DAILY:
                # Special handling because the template has a `-` inserted
                content = section.get_content().strip()
                if content and content != "-":
                    kept_sections.append(section)
                continue

            if not self._is_content_empty(section.get_content()):
                kept_sections.append(section)

        # If all of the page sections have been removed, delete the file entirely
        if not kept_sections:
            logger.info(f"Deleting the now empty {self.filepath}")
            self.filepath.unlink()
            self.sections = []
            self._initial_frontmatter_hash = self._hash_frontmatter()
            self._initial_content_hash = self._hash_content()
        else:
            # Reconstruct page with only `kept_sections`
            self.sections = []
            self.update_template_dates()
            for section in kept_sections:
                self.put_section(section)
