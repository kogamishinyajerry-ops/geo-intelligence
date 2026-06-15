from datetime import datetime, timezone

from geo.evidence.schema import SCHEMA_VERSION, BuyerSegment, Capture
from geo.evidence.store import EvidenceStore


def test_make_id_deterministic_and_readable():
    ts = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)
    a = Capture.make_id("doubao", BuyerSegment.A, ts, "hello")
    b = Capture.make_id("doubao", "A", ts, "hello")  # enum 与 str 等价
    assert a == b
    assert a.startswith("doubao-A-20260614T120000Z-")


def test_make_id_distinguishes_answers():
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert Capture.make_id("e", "B", ts, "x") != Capture.make_id("e", "B", ts, "y")


def test_naive_timestamp_coerced_to_utc():
    cap = Capture(
        id="x",
        engine="e",
        query="q",
        buyer_segment=BuyerSegment.B,
        timestamp=datetime(2026, 1, 1, 0, 0, 0),  # naive
        raw_answer="hi",
    )
    assert cap.timestamp.tzinfo is not None
    assert cap.schema_version == SCHEMA_VERSION
    assert cap.is_mock is False


def test_store_roundtrip(tmp_path):
    store = EvidenceStore(tmp_path)
    ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
    cap = Capture(
        id=Capture.make_id("e", "B", ts, "a"),
        engine="e",
        query="q",
        buyer_segment=BuyerSegment.B,
        timestamp=ts,
        raw_answer="answer body",
        named_brands=["Goldbelly"],
    )
    path = store.save(cap)
    assert path.exists()
    loaded = store.load(cap.id)
    assert loaded.raw_answer == "answer body"
    assert loaded.named_brands == ["Goldbelly"]
    assert loaded.buyer_segment == BuyerSegment.B
    assert len(store.load_all()) == 1
