import gup

def test_next_free_version(monkeypatch):
    existing = {"v1.2.3", "v1.2.4"}

    def fake_tag_exists(tag):
        return tag in existing

    monkeypatch.setattr(gup, "tag_exists", fake_tag_exists)

    assert gup.next_free_version(1, 2, 3) == "v1.2.5"

