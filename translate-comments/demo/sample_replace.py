"""This module is a sample that demonstrates how to construct a greeting message."""


def greet(name):
    """Receive the name and reply with a greeting."""
    # Create a string to serve as the basis for the greeting
    message = "Hello, " + name  # We've decided on a policy of not adding exclamation points at the end.
    return message
