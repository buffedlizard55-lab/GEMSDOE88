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


@pytest.mark.parametrize("bad_score", [
    "-0.4413", "+0.4413", "0.4413%", "score: 0.4413", "0.4413e2",
    "0.44130", "1.0001", "NaN", "inf", "0.4413 0.3904", "",
])
def test_invalid_score_never_overwrites_snapshot(tmp_path, bad_score):
    path = tmp_path / "feed.json"
    update(path, FAKE_HTML)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="previous snapshot preserved"):
        update(path, FAKE_HTML.replace("0.4413", bad_score))
    assert path.read_bytes() == before


@pytest.mark.parametrize("rank", ["#2", "#5", "#0", "#-4", "#4 extra"])
def test_invalid_later_rank_not_hidden_by_valid_top_three(rank):
    extra = f"<tr><td>{rank}</td><td>team</td><td>Delta</td><td>0.3000</td></tr>"
    html = FAKE_HTML.replace("</table>", extra + "</table>")
    with pytest.raises(ValueError, match="previous snapshot preserved"):
        parse_leaderboard(html)


def test_invalid_later_score_not_silently_skipped():
    extra = "<tr><td>#4</td><td>team</td><td>Delta</td><td>bad</td></tr>"
    with pytest.raises(ValueError, match="previous snapshot preserved"):
        parse_leaderboard(FAKE_HTML.replace("</table>", extra + "</table>"))


def test_score_range_endpoints_and_ties():
    html = FAKE_HTML.replace("0.4413", "1.0000").replace("0.3904", "0.0000").replace("0.3894", "0.0000")
    rows = parse_leaderboard(html)
    assert [r["public_dti"] for r in rows] == [1.0, 0.0, 0.0]


def test_parser_does_not_fetch_without_explicit_html(tmp_path):
    path = tmp_path / "feed.json"
    with pytest.raises(RuntimeError, match="disabled"):
        update(path)
    assert not path.exists()


@pytest.mark.parametrize("extra", [
    "<tr><td>#4</td><td>team</td><td>Delta</td></tr>",
    "<tr><td>#4</td><td>team</td><td></td><td>0.3000</td></tr>",
])
def test_incomplete_ranked_rows_preserve_snapshot(tmp_path, extra):
    path = tmp_path / "feed.json"
    update(path, FAKE_HTML)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="previous snapshot preserved"):
        update(path, FAKE_HTML.replace("</table>", extra + "</table>"))
    assert path.read_bytes() == before
