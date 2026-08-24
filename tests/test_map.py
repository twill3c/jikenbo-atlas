# T-401..T-403(F-08)— 事件現場座標と地図ビューの整合ゲート
#
# 地理定数(公知、2026-08-24 記載):
#   英国 bbox: lat 49.8–59.5, lon -8.7–1.8
#   大ロンドン bbox: lat 51.26–51.71, lon -0.53–0.36
#   チャリング・クロス(ロンドンの距離基準点): 51.5074, -0.1278
import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
CANON = ROOT / "data" / "canon_cases.json"
INDEX = ROOT / "web" / "data" / "index.json"

pytestmark = pytest.mark.integration

UK = (49.8, 59.5, -8.7, 1.8)
LONDON = (51.26, 51.71, -0.53, 0.36)
CHARING_CROSS = (51.5074, -0.1278)


def in_box(lat, lon, box):
    return box[0] <= lat <= box[1] and box[2] <= lon <= box[3]


def km_from_cc(lat, lon):
    # 平面近似で十分(判定閾値 25/60km に対し誤差 <1%)
    dy = (lat - CHARING_CROSS[0]) * 111.32
    dx = (lon - CHARING_CROSS[1]) * 111.32 * math.cos(math.radians(51.5))
    return math.hypot(dx, dy)


@pytest.fixture(scope="module")
def cases():
    return json.loads(CANON.read_text(encoding="utf-8"))["cases"]


def test_t401_site_everywhere(cases):
    for c in cases:
        s = c.get("site")
        assert s, c["id"]
        assert isinstance(s["lat"], (int, float)) and isinstance(s["lon"], (int, float)), c["id"]
        assert s["label"], c["id"]
        assert isinstance(s["approx"], bool), c["id"]


def test_t402_region_consistency(cases):
    for c in cases:
        s = c["site"]
        lat, lon = s["lat"], s["lon"]
        if c["region"] == "海外":
            assert not in_box(lat, lon, UK), c["id"]
        elif c["region"] == "ロンドン":
            assert in_box(lat, lon, LONDON), c["id"]
        elif c["region"] == "ロンドン近郊":
            assert in_box(lat, lon, UK) and km_from_cc(lat, lon) <= 60, c["id"]
        else:  # 地方
            assert in_box(lat, lon, UK) and km_from_cc(lat, lon) > 25, c["id"]


def test_t403_map_page_and_propagation(cases):
    if not INDEX.exists():
        pytest.skip("web 未ビルド")
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    assert all(c.get("site") for c in idx["cases"])
    html = (ROOT / "web" / "map.html").read_text(encoding="utf-8")
    js = (ROOT / "web" / "map.js").read_text(encoding="utf-8")
    assert "leaflet" in html.lower()
    assert 'id="map"' in html
    assert "data/index.json" in js
