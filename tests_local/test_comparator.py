from app.services.testing.comparator import compare


def test_exact():
    assert compare("1 2 3", "1 2 3")
    assert not compare("1 2 3\n", "1 2 3\nextra")


def test_tokens():
    assert compare("1   2\n3", "1 2 3", mode="tokens")


def test_ignore_whitespace():
    assert compare("abc\n", "a b c", mode="ignore_whitespace")


def test_float():
    assert compare("1.0 2.5", "1 2.5", mode="float")
