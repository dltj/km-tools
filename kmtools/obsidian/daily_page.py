from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from kmtools.obsidian.page_base import ObsidianPageBase

from .sections import FieldSection


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
