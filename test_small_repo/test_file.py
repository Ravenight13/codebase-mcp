"""Test file for indexing verification.

This is a simple Python file to test the complete indexing workflow
including chunking and embedding generation.
"""


def hello_world():
    """A simple test function."""
    return "Hello, World!"


def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


class TestClass:
    """A simple test class."""

    def __init__(self, name: str):
        """Initialize the test class."""
        self.name = name

    def greet(self) -> str:
        """Return a greeting."""
        return f"Hello, {self.name}!"


if __name__ == "__main__":
    print(hello_world())
    print(add_numbers(5, 3))
    test = TestClass("Developer")
    print(test.greet())
