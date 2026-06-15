from geo.parsing import extract

WL = {
    "segment_B_en": [
        {"name": "Harry & David", "aliases": ["Harry & David", "Harry and David"]},
        {"name": "Goldbelly", "aliases": ["Goldbelly"]},
    ]
}


def test_extract_links_dedup_and_strip():
    t = "see https://a.com/x, and http://b.org). also https://a.com/x again"
    links = extract.extract_links(t)
    assert links == ["https://a.com/x", "http://b.org"]  # 保序 + 去重 + 剥尾标点


def test_extract_brands_order_alias_dedup():
    t = "First Goldbelly is great, then Harry and David, and Goldbelly again."
    out = extract.extract_brands(t, WL, "segment_B_en")
    assert out == ["Goldbelly", "Harry & David"]  # 按首次出现，alias→canonical，去重


def test_extract_brands_empty_when_none():
    assert extract.extract_brands("no tracked brands here", WL, "segment_B_en") == []


def test_extract_brands_alias_maps_to_canonical():
    assert extract.extract_brands("Harry & David rocks", WL, "segment_B_en") == ["Harry & David"]
