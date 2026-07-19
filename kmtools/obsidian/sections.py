import re
from dataclasses import dataclass, field

FIELD_PATTERN = re.compile(r"^(\w[\w\s]*)::[ \t]*(.*?)[ \t]*$", re.MULTILINE)


@dataclass
class Section:
    heading: str | None
    content: str

    def heading_line(self) -> str | None:
        if self.heading is None:
            return None
        return f"## {self.heading}"

    def get_content(self) -> str:
        return self.content


@dataclass
class FieldSection(Section):
    fields: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Parse fields from content, then discard content."""
        self.fields = {
            m.group(1): m.group(2) for m in FIELD_PATTERN.finditer(self.content)
        }
        self.content = ""  # fields is now the sole source of truth

    def get_content(self) -> str:
        """Builds content string from fields on demand."""
        return "\n".join(f"{key}:: {value}" for key, value in self.fields.items())

    def set_field(self, key: str, value: str):
        self.fields[key] = value
