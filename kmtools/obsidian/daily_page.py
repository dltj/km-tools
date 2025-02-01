import re
from datetime import datetime, timedelta

import yaml

from kmtools.obsidian.page_base import ObsidianPageBase


class ObsidianDailyPage(ObsidianPageBase):
    SECTION_START_MARKDOWN = r"^## Yesterday\'s readings\s*$"
    SECTION_END_DAILY_NOTES = r"^## Daily notes\s$"

    def __init__(self, file_name: str) -> None:
        self.readings_content = ""
        self.content_before = ""
        self.content_after = ""
        self.readings: list = []
        super().__init__(file_name)

    def _read_file(self):
        super()._read_file()

        # Use regex to find the section start and end based on a blank line
        section_start_regex = re.compile(self.SECTION_START_MARKDOWN, re.MULTILINE)
        section_end_regex = re.compile(self.SECTION_END_DAILY_NOTES, re.MULTILINE)

        # Find the section
        start_match = section_start_regex.search(self.content)
        if not start_match:
            self.content_before = self.content
            return

        # Content before the section
        self.content_before = self.content[: start_match.start()]

        # Find the section end
        following_text = self.content[start_match.end() :]
        end_match = section_end_regex.search(following_text)
        if end_match:
            # Content between the start and end blank line
            self.readings_content = following_text[: end_match.start()].strip()
            # Content after the section
            self.content_after = following_text[end_match.end() :]
        else:
            # If no blank line is found, take everything after the start
            self.readings_content = following_text.strip()
            self.content_after = ""

        # Convert a markdown list in `readings_content` to a Python list.
        # Split the content by new lines, and extract lines starting with '-'
        lines = self.readings_content.strip().splitlines()
        self.readings = [
            line.lstrip("- ").strip() for line in lines if line.startswith("- ")
        ]

        # Set/fix dates in content_before
        weekday_name = datetime.now().strftime("%A")
        date_14_days_ago = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        date_7_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        date_yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        date_tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        date_today = datetime.now().strftime("%d-%b")

        output_lines = []
        for line in self.content_before.splitlines():
            if line.startswith("Weekday::"):
                output_lines.append(f"Weekday:: {weekday_name}")
                continue
            if line.startswith("Two weeks ago::"):
                output_lines.append(f"Two weeks ago:: [[{date_14_days_ago}]]")
                continue
            if line.startswith("Last week::"):
                output_lines.append(f"Last week:: [[{date_7_days_ago}]]")
                continue
            if line.startswith("Yesterday::"):
                output_lines.append(f"Yesterday:: [[{date_yesterday}]]")
                continue
            if line.startswith("Tomorrow::"):
                output_lines.append(f"Tomorrow:: [[{date_tomorrow}]]")
                continue
            if line.startswith("LIST FROM #"):
                output_lines.append(f"LIST FROM #{date_today}")
                continue
            output_lines.append(line)
        self.content_before = "\n".join(output_lines)

    def save(self):
        self.readings_content = "\n".join(f"- {item}" for item in self.readings)
        with self.filepath.open("w", encoding="utf-8") as f:
            frontmatter_text = yaml.safe_dump(self.frontmatter, sort_keys=False)
            full_content = f"---\n{frontmatter_text}---"
            full_content += self.content_before
            full_content += f"\n## Yesterday's readings\n{self.readings_content}\n\n"
            full_content += f"## Daily notes\n{self.content_after.strip()}"
            f.write(full_content)
