import pytest
from update_leaderboard import parse_leaderboard, update

FAKE_HTML = """<html><table><tr><th>Rank</th><th>Team members</th><th>Participant</th><th>Best public DW-<br>Tversky</th></tr>
<tr><td>#1</td><td>team</td><td>Alpha</td><td>0.4413</td></tr>
<tr><td>#2</td><td>team</td><td>Beta</td><td>0.3904</td></tr>
<tr><td>#3</td><td>team</td><td>Gamma</td><td>0.3894</td></tr></table></html>"""


def test_parser_and_atomic_snapshot(tmp_path):
    p = tmp_path / "feed.json"
    s = update(p, FAKE_HTML)
    assert s["observed_top10"][0] == dict(
        rank=1, participant="Alpha", public_dti=0.4413
    )
    original = p.read_bytes()
    with pytest.raises(ValueError, match="previous snapshot preserved"):
        update(p, "<html>Login required</html>")
    assert p.read_bytes() == original


def test_parser_rejects_unsorted_and_empty_table():
    assert parse_leaderboard(FAKE_HTML)[2]["rank"] == 3
    with pytest.raises(ValueError):
        parse_leaderboard(FAKE_HTML.replace("0.3904", "0.9999"))
