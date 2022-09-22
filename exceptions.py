class EndpointIsUnavailable(Exception):
    """Called when the API returns a code other than 200."""
    pass


class APIResponseIsIncorrect(Exception):
    """
    Called when the api returns a response that does not meet expectations.
    """
    pass


class UnexpectedStatus(Exception):
    """Called when receiving a status that is not in HOMEWORK_STATUSES."""
    pass

