"""동결 인수 테스트 — SPEC-cache.md 의 8개 AC 만 검사한다.

★ 이 파일은 **구현이 존재하기 전에** SPEC 만 보고 작성되었고, 구현을 본 뒤 수정하지 않는다.
따라서 실패 = 구현이 자기가 받은 계약을 못 지킨 것.

★ 의도적으로 **AC 가 말한 것만** 검사한다. PREREG 의 F1~F8 (recency 갱신 여부, __len__ 의
만료 항목 처리, TTL 경계, 지연 제거 등)은 계약이 정하지 않았으므로 **여기서 검사하지 않는다.**
그것을 검사하면 자유 공간을 테스트로 몰래 좁히는 것이고, 이 실험의 측정 대상 자체가 사라진다.
"""

import pytest

from ttl_cache import TtlCache


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def make(capacity=2, ttl=10.0, clock=None):
    c = clock or Clock()
    return TtlCache(capacity=capacity, ttl=ttl, time_fn=c), c


# --- AC-01 --------------------------------------------------------------
def test_ac01_put_then_get_returns_value():
    c, _ = make()
    c.put("k", "v")
    assert c.get("k") == "v"


def test_ac01_distinct_keys_are_independent():
    c, _ = make(capacity=4)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    assert c.get("b") == 2


# --- AC-02 --------------------------------------------------------------
def test_ac02_missing_key_raises_keyerror():
    c, _ = make()
    with pytest.raises(KeyError):
        c.get("never-inserted")


# --- AC-03 --------------------------------------------------------------
def test_ac03_capacity_is_not_exceeded():
    c, _ = make(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    alive = 0
    for k in ("a", "b", "c"):
        try:
            c.get(k)
            alive += 1
        except KeyError:
            pass
    assert alive <= 2


# --- AC-04 --------------------------------------------------------------
def test_ac04_evicts_least_recently_used():
    c, _ = make(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    with pytest.raises(KeyError):
        c.get("a")
    assert c.get("b") == 2
    assert c.get("c") == 3


# --- AC-05 --------------------------------------------------------------
def test_ac05_get_counts_as_use():
    c, _ = make(capacity=2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    with pytest.raises(KeyError):
        c.get("b")
    assert c.get("a") == 1
    assert c.get("c") == 3


# --- AC-06 --------------------------------------------------------------
def test_ac06_expired_entry_is_not_returned():
    c, clock = make(capacity=4, ttl=10.0)
    c.put("k", "v")
    clock.advance(10.5)          # ttl 을 '초과해' 흐른다 — 경계값은 계약이 안 정했다
    with pytest.raises(KeyError):
        c.get("k")


def test_ac06_entry_well_within_ttl_is_returned():
    c, clock = make(capacity=4, ttl=10.0)
    c.put("k", "v")
    clock.advance(1.0)
    assert c.get("k") == "v"


# --- AC-07 --------------------------------------------------------------
def test_ac07_reput_replaces_value():
    c, _ = make(capacity=2)
    c.put("k", "v1")
    c.put("k", "v2")
    assert c.get("k") == "v2"


def test_ac07_reput_does_not_grow_the_cache():
    c, _ = make(capacity=2)
    c.put("a", 1)
    c.put("a", 2)
    c.put("b", 3)
    assert c.get("a") == 2
    assert c.get("b") == 3


# --- AC-08 --------------------------------------------------------------
@pytest.mark.parametrize("capacity,ttl", [
    (0, 10.0),
    (-1, 10.0),
    (2, 0.0),
    (2, -1.0),
])
def test_ac08_invalid_config_rejected(capacity, ttl):
    with pytest.raises(ValueError):
        TtlCache(capacity=capacity, ttl=ttl, time_fn=Clock())
