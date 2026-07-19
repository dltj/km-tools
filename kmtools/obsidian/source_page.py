from kmtools.obsidian.page_base import ObsidianPageBase
from kmtools.util.obsidian import title_to_page


class ObsidianSourcePage(ObsidianPageBase):
    SEC_PREAMBLE = None

    def __init__(self, page_title: str) -> None:
        if page_title:
            self.file_name = title_to_page(page_title) + ".md"
        super().__init__(self.file_name)
        self.frontmatter["type"] = "Source"
