import pytest
from hypothesis import given
from hypothesis import strategies as st

from eav.logic.slug import SLUGFIELD_MAX_LENGTH, generate_slug


@given(st.text())
def test_generate_slug(name: str) -> None:
    """Ensures slug generation works properly."""
    slug = generate_slug(name)

    assert slug


@given(st.text(min_size=SLUGFIELD_MAX_LENGTH))
def test_generate_long_slug_text(name: str) -> None:
    """Ensures a slug isn't generated longer than maximum allowed length."""
    slug = generate_slug(name)

    assert len(slug) <= SLUGFIELD_MAX_LENGTH


def test_generate_slug_uniqueness() -> None:
    """Test that generate_slug() produces unique slugs for different inputs.

    This test ensures that even similar inputs result in unique slugs,
    and that the number of unique slugs matches the number of inputs.
    """
    inputs = ["age #", "age %", "age $", "age @", "age!", "age?", "age 😊"]

    generated_slugs: dict[str, str] = {}
    for input_str in inputs:
        slug = generate_slug(input_str)
        assert slug not in generated_slugs.values(), (
            f"Duplicate slug '{slug}' generated for input '{input_str}'"
        )
        generated_slugs[input_str] = slug

    assert len(generated_slugs) == len(
        inputs,
    ), "Number of unique slugs doesn't match number of inputs"


@pytest.mark.parametrize(
    "input_str",
    [
        "01 age",
        "? age",
        "age 😊",
        "class",
        "def function",
        "2nd place",
        "@username",
        "user-name",
        "first.last",
        "snake_case",
        "CamelCase",
        "  ",  # Empty
    ],
)
def test_generate_slug_valid_identifier(input_str: str) -> None:
    """Test that generate_slug() produces valid Python identifiers.

    This test ensures that the generated slugs are valid Python identifiers
    for a variety of input strings, including those with numbers, special
    characters, emojis, and different naming conventions.

    Args:
        input_str (str): The input string to test.
    """
    slug = generate_slug(input_str)
    assert slug.isidentifier(), (
        f"Generated slug '{slug}' for input '{input_str}' "
        + "is not a valid Python identifier"
    )
