import gitgo.__main__ as gitgo

def test_clamp_timeout_valid():
    assert gitgo.clamp_timeout("10") == "10"
    assert gitgo.clamp_timeout("100") == "60"
    assert gitgo.clamp_timeout("0") == "1"

def test_clamp_timeout_invalid():
    assert gitgo.clamp_timeout("abc") == "12"
    assert gitgo.clamp_timeout("") == "12"

def test_is_printable_no_space():
    assert gitgo.is_printable_no_space("abcDEF123")
    assert not gitgo.is_printable_no_space("abc def")
    assert not gitgo.is_printable_no_space("abc\n")

def test_enforce_summary_limit_short():
    msg = "Short summary\n\nBody"
    assert gitgo.enforce_summary_limit(msg) == msg

def test_enforce_summary_limit_long():
    long = "A" * 100
    result = gitgo.enforce_summary_limit(long)
    assert len(result.splitlines()[0]) <= 72
