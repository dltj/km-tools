# import collections
import re
from abc import abstractmethod

from config import config

# Annotation = collections.namedtuple(
#     "Annotation",
#     [
#         "id",
#         "uri",
#         "annotation",
#         "created",
#         "updated",
#         "quote",
#         "tags",
#         "document_title",
#         "link_html",
#         "link_incontext",
#         "hidden",
#         "flagged",
#     ],
# )


class Origin:
    """An origin of resources"""

    origin_name = "UNDEFINED"
    origin_table = "UNDEFINED"
    origin_key = "UNDEFINED"
    obsidian_tagless = False

    def __init__(self) -> None:
        pass

    @abstractmethod
    def make_resource(self, uri: str):
        """
        Factory method for creating a Resource instance.

        :param uri: URI of instance to create
        """
        raise NotImplementedError("Implement resource in subclass!")


class Resource:
    """A resource"""

    origin: Origin = None

    def __init__(
        self,
        uri,
        title=None,
        headline=None,
        publisher=None,
        description=None,
        tags=None,
    ) -> None:
        self.uri = uri
        self.title = title
        self.headline = headline if headline else title
        self.publisher = publisher
        self.description = description
        self.tags = tags
        self.annotations = list()

    def __getattr__(self, name):
        # if name in self.
        #     return self[name]
        for action in config.actions:
            if name in action.attributes_supplied:
                return action.attribute_read(self, name)

        raise AttributeError("No such attribute: " + name)


class WebResource(Resource):
    """A web resource"""

    def __init__(
        self,
        uri,
        title=None,
        description=None,
        tags=None,
        public=None,
    ) -> None:
        title_scan = re.compile(
            r"""(.*?)\s+          # headline proper (group 1)
                (\[(.*?)\])?      # optionally, a comment/description in square brackets (group 3)
                (\s+(.*?))?\|\s+  # optionally, any other parts of the headline before the vertical bar (group 5)
                (.*)              # publisher after the vertical bar (group 6)
            """,
            re.X,
        )

        headline = None
        publisher = None

        if title:
            if match := title_scan.match(title):
                headline = f"{match.group(1)}"
                if match.group(3):
                    headline = f"{headline} – {match.group(3)}"
                description = f"_{match.group(5)}_\n\n{description}"
                publisher = match.group(6)
            else:
                headline = title
                publisher = None

        super().__init__(
            uri=uri,
            title=title,
            headline=headline,
            publisher=publisher,
            description=description,
            tags=tags,
        )
        self.public = public
        self.annotation_url = None

    @property
    def url(self):
        return self.uri


class Annotation(Resource):
    """An annotation on a resource"""

    def __init__(
        self,
        uri,
        source: Resource = None,
        title=None,
        quote=None,
        annotation=None,
        tags=None,
        public=None,
    ) -> None:
        super().__init__(uri=uri, title=title, tags=tags, description=annotation)
        self.source = source
        self.quote = quote
        self.annotation = annotation
        self.public = public

    @abstractmethod
    def output_annotation(self, fd):
        raise NotImplementedError("output_annotation not implemented")
