"""
Handled exceptions from the Knowledge Management commands.
"""

import json


class KMException(Exception):
    """
    Base class for Knowledge Management exceptions.
    """

    default_detail = "A server error occurred."
    detail = None

    def __init__(self, detail=None):
        if detail is None:
            self.detail = self.default_detail
        super().__init__(detail)

    def __str__(self):
        return str(self.detail)


class TweetError(KMException):
    """Exception raised for Twitter API errors.

    Attributes:
        message -- explanation of the error
    """

    default_detail = "Error calling twitter"

    def __init__(self, status_code, response_body):
        message = f"(HTTP {status_code}): {response_body}"
        if str(status_code).isnumeric():
            try:
                response = json.loads(response_body)
            except json.JSONDecodeError:
                pass
            else:
                code = response["errors"][0]["code"]
                twtr_msg = response["errors"][0]["message"]
                message = f"Twitter returned HTTP {status_code} with internal code {code} and message '{twtr_msg}'"
        self.detail = message
        super().__init__(message)


class PinboardError(KMException):
    """Exception raised for Pinboard API errors.

    Attributes:
        status_code: HTTP status code
        response_body: HTTP response body from the endpoint
    """

    default_detail = "Error calling Pinboard"

    def __init__(self, status_code, response_body):
        message = f"(HTTP {status_code}): {response_body}"
        self.detail = message
        super().__init__(message)


class ResourceNotFoundError(KMException):
    """Exception raised when a search of resources for a URL returns more than one row."""

    default_detail = "Resource not found for URL"

    def __init__(self, uri=None):
        message = self.default_detail
        if uri:
            message = f"Resource not found for URL {uri}"
        self.detail = message
        super().__init__(message)


class MoreThanOneError(KMException):
    """Exception raised when a search of sources for a URL returns more than one row."""

    default_detail = "More than one URL returned"

    def __init__(self, uri=None):
        message = self.default_detail
        if uri:
            message = f"More than one resource found for URL {uri}"
        self.detail = message
        super().__init__(message)


class HypothesisError(KMException):
    """Exception raised for Hypothesis API errors.

    Attributes:
        message -- explanation of the error
    """

    default_detail = "Error calling Hypothesis"

    def __init__(self, status_code, response_body):
        message = f"(HTTP {status_code}): {response_body}"
        if str(status_code).isnumeric():
            try:
                response = json.loads(response_body)
            except json.JSONDecodeError:
                pass
            else:
                status = response["status"]
                reason = response["reason"]
                message = (
                    f"Twitter returned HTTP {status_code} "
                    f"with internal status {status} "
                    f"and message '{reason}'"
                )
        self.detail = message
        super().__init__(message)


class WaybackError(KMException):
    """Exception raised for Wayback API errors.

    Attributes:
        status_code: HTTP status code
        response_body: HTTP response body from the endpoint
    """

    default_detail = "Error calling Wayback"

    def __init__(self, status_code, response_body):
        message = f"(HTTP {status_code}): {response_body}"
        if str(status_code).isnumeric():
            try:
                response = json.loads(response_body)
            except json.JSONDecodeError:
                pass
            else:
                exception = response["exception"]
                detail = response["status_ext"]
                message = (
                    f"Wayback returned HTTP {status_code} "
                    f"with internal error '{exception}'' "
                    f"and additional detail '{detail}'"
                )
        self.detail = message
        super().__init__(message)


class SummarizeError(KMException):
    """Exception raised for Summarize errors.

    Attributes:
        status_code: HTTP status code
        response_body: HTTP response body from the endpoint
    """

    default_detail = "Error calling Wayback"

    def __init__(self, message):
        self.detail = message
        super().__init__(message)


class ActionError(KMException):
    """Exception raised for Actions.

    Args:
        KMException (_type_): _description_
    """

    def __init__(self, message):
        self.detail = message
        super().__init__(message)


class ActionSkip(ActionError):
    """Exception raised when a commit to the process_status table should be skipped."""

    default_detail = "Skip process_table update"

    def __init__(self, message):
        self.detail = message
        super().__init__(message)
