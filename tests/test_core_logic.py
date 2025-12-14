import gup.__main__ as gup

def test_clamp_timeout_valid():
    assert gup.clamp_timeout("10") == "10"
    assert gup.clamp_timeout("100") == "60"
    assert gup.clamp_timeout("0") == "1"

def test_clamp_timeout_invalid():
    assert gup.clamp_timeout("abc") == "12"
    assert gup.clamp_timeout("") == "12"

def test_is_printable_no_space():
    assert gup.is_printable_no_space("abcDEF123")
    assert not gup.is_printable_no_space("abc def")
    assert not gup.is_printable_no_space("abc\n")

def test_enforce_summary_limit_short():
    msg = "Short summary\n\nBody"
    assert gup.enforce_summary_limit(msg) == msg

def test_enforce_summary_limit_long():
    long = "A" * 100
    result = gup.enforce_summary_limit(long)
    assert len(result.splitlines()[0]) <= 72
