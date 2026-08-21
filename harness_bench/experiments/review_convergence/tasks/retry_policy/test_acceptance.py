"""인수 테스트 — SPEC-retry-policy.md 만 보고 작성. 구현 존재 전에 작성됨.

동결 규칙: 구현을 본 뒤에는 이 파일을 수정하지 않는다. 이것이 "테스트가 구현에 맞춰졌다"는
반박을 막는 유일한 장치다. (그 이상은 못 막는다 — DESIGN.md §4)

각 테스트는 정확히 하나의 AC 를 검사하고 함수명에 AC 번호를 담는다. 계층(요구사항/관례)은
여기 표시하지 않는다 — 구현자에게 어떤 AC 가 덜 중요한지 알려주지 않기 위해 DESIGN.md 에만 둔다.
"""

from __future__ import annotations

import pytest

from retry_policy import CircuitOpenError, RetryPolicy


class Retryable(Exception):
    pass


class Fatal(Exception):
    pass


class Clock:
    """주입되는 단조 시계. 테스트가 시간을 직접 전진시킨다."""

    def __init__(self, t: float = 1000.0) -> None:
        self.t = t
        self.slept: list[float] = []

    def time(self) -> float:
        return self.t

    def sleep(self, d: float) -> None:
        self.slept.append(d)
        self.t += d

    def advance(self, d: float) -> None:
        self.t += d


def make(clock: Clock | None = None, rand=lambda: 1.0, **over):
    """기본 설정의 정책. rand 기본값 1.0 은 지터를 항등으로 만들어
    백오프 계산 자체를 먼저 검증할 수 있게 한다 (AC-07 은 별도로 검사)."""
    c = clock or Clock()
    cfg = dict(
        max_attempts=3,
        base_delay=1.0,
        max_delay=100.0,
        retryable=(Retryable,),
        failure_threshold=100,   # 브레이커가 재시도 테스트를 방해하지 않도록
        cooldown=10.0,
        time_fn=c.time,
        sleep_fn=c.sleep,
        rand_fn=rand,
    )
    cfg.update(over)
    return RetryPolicy(**cfg), c


# ---------------------------------------------------------------- 재시도

def test_ac01_success_calls_once_and_never_sleeps():
    p, c = make()
    calls = []

    def fn():
        calls.append(1)
        return "ok"

    assert p.call(fn) == "ok"
    assert len(calls) == 1
    assert c.slept == []


def test_ac02_max_attempts_includes_the_first_call():
    p, c = make(max_attempts=3)
    calls = []

    def fn():
        calls.append(1)
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(fn)
    assert len(calls) == 3


def test_ac03_propagates_the_last_exception_object():
    p, _ = make(max_attempts=3)
    raised = []

    def fn():
        e = Retryable(f"attempt-{len(raised)}")
        raised.append(e)
        raise e

    with pytest.raises(Retryable) as got:
        p.call(fn)
    assert got.value is raised[-1]


def test_ac04_does_not_sleep_after_the_final_attempt():
    p, c = make(max_attempts=3)

    def fn():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(fn)
    assert len(c.slept) == 2


def test_ac05_non_retryable_propagates_immediately_without_retry():
    p, c = make(max_attempts=3)
    calls = []

    def fn():
        calls.append(1)
        raise Fatal("nope")

    with pytest.raises(Fatal):
        p.call(fn)
    assert len(calls) == 1
    assert c.slept == []


# ---------------------------------------------------------------- 백오프/지터

def test_ac06_delay_grows_exponentially():
    p, c = make(max_attempts=4, base_delay=1.0, max_delay=100.0, rand=lambda: 1.0)

    def fn():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(fn)
    assert c.slept == [1.0, 2.0, 4.0]


def test_ac07_jitter_is_applied_after_the_cap():
    """rand=0.5, base=1, cap=5. 4번째 재시도의 기준 지연은 min(8,5)=5 이므로 2.5.
    상한 전에 지터를 곱했다면 min(8*0.5, 5) = 4.0 이 나온다."""
    p, c = make(max_attempts=5, base_delay=1.0, max_delay=5.0, rand=lambda: 0.5)

    def fn():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(fn)
    assert c.slept == [0.5, 1.0, 2.0, 2.5]


def test_ac08_cap_actually_truncates():
    p, c = make(max_attempts=5, base_delay=1.0, max_delay=5.0, rand=lambda: 1.0)

    def fn():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(fn)
    assert c.slept == [1.0, 2.0, 4.0, 5.0]


# ---------------------------------------------------------------- 브레이커

def test_ac09_breaker_counts_calls_not_attempts():
    """max_attempts=3, threshold=2. 실패 call 1회(내부 3시도) 후에도 열리면 안 된다."""
    p, _ = make(max_attempts=3, failure_threshold=2)

    def fn():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(fn)
    assert p.state == "closed"


def test_ac10_opens_when_consecutive_failures_reach_threshold():
    p, _ = make(max_attempts=1, failure_threshold=2)

    def fn():
        raise Retryable("boom")

    for _ in range(2):
        with pytest.raises(Retryable):
            p.call(fn)
    assert p.state == "open"


def test_ac11_open_circuit_blocks_without_calling_fn():
    p, c = make(max_attempts=1, failure_threshold=1)
    calls = []

    def fn():
        calls.append(1)
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(fn)
    assert p.state == "open"

    before = len(calls)
    with pytest.raises(CircuitOpenError):
        p.call(fn)
    assert len(calls) == before
    assert c.slept == []


def test_ac12_success_resets_the_consecutive_failure_counter():
    p, _ = make(max_attempts=1, failure_threshold=3)

    def bad():
        raise Retryable("boom")

    def good():
        return "ok"

    for _ in range(2):
        with pytest.raises(Retryable):
            p.call(bad)
    assert p.call(good) == "ok"
    for _ in range(2):
        with pytest.raises(Retryable):
            p.call(bad)
    assert p.state == "closed"


def test_ac13_transitions_to_half_open_after_cooldown():
    p, c = make(max_attempts=1, failure_threshold=1, cooldown=10.0)
    seen_state = []

    def bad():
        raise Retryable("boom")

    def probe():
        seen_state.append(p.state)
        return "ok"

    with pytest.raises(Retryable):
        p.call(bad)
    assert p.state == "open"

    c.advance(10.0)
    assert p.call(probe) == "ok"
    assert seen_state == ["half_open"]


def test_ac14_half_open_success_closes_the_circuit():
    p, c = make(max_attempts=1, failure_threshold=2, cooldown=10.0)

    def bad():
        raise Retryable("boom")

    for _ in range(2):
        with pytest.raises(Retryable):
            p.call(bad)
    assert p.state == "open"

    c.advance(10.0)
    assert p.call(lambda: "ok") == "ok"
    assert p.state == "closed"

    # 카운터가 0 이므로 실패 1회로는 다시 열리지 않는다 (threshold=2).
    with pytest.raises(Retryable):
        p.call(bad)
    assert p.state == "closed"


def test_ac15_half_open_failure_reopens_and_restarts_cooldown():
    p, c = make(max_attempts=1, failure_threshold=1, cooldown=10.0)

    def bad():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(bad)
    assert p.state == "open"

    c.advance(10.0)
    with pytest.raises(Retryable):
        p.call(bad)          # half-open 시험 호출 실패
    assert p.state == "open"

    c.advance(9.0)           # 재시작된 cooldown 이 아직 안 지남
    with pytest.raises(CircuitOpenError):
        p.call(bad)

    c.advance(1.0)           # 이제 지남
    assert p.call(lambda: "ok") == "ok"


def test_ac16_half_open_allows_only_one_trial_call():
    """시험 호출이 진행 중일 때 재진입한 call 은 차단되어야 한다."""
    p, c = make(max_attempts=1, failure_threshold=1, cooldown=10.0)
    inner = {}

    def bad():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(bad)
    c.advance(10.0)

    def trial():
        # 시험 호출이 아직 반환하지 않은 상태에서 두 번째 호출을 시도한다.
        try:
            p.call(lambda: "second")
            inner["result"] = "allowed"
        except CircuitOpenError:
            inner["result"] = "blocked"
        return "ok"

    assert p.call(trial) == "ok"
    assert inner["result"] == "blocked"


def test_ac17_non_retryable_still_counts_toward_the_breaker():
    p, _ = make(max_attempts=3, failure_threshold=2)

    def fn():
        raise Fatal("nope")

    for _ in range(2):
        with pytest.raises(Fatal):
            p.call(fn)
    assert p.state == "open"


def test_ac18_circuit_open_error_does_not_count_as_a_failure():
    """열린 회로가 자기 자신을 갱신하면 영원히 안 닫힌다."""
    p, c = make(max_attempts=1, failure_threshold=1, cooldown=10.0)

    def bad():
        raise Retryable("boom")

    with pytest.raises(Retryable):
        p.call(bad)
    assert p.state == "open"

    # cooldown 동안 차단된 호출을 여러 번 시도해도 cooldown 이 밀리면 안 된다.
    for _ in range(5):
        with pytest.raises(CircuitOpenError):
            p.call(bad)

    c.advance(10.0)
    assert p.call(lambda: "ok") == "ok"
    assert p.state == "closed"


# ---------------------------------------------------------------- 입력 검증

@pytest.mark.parametrize(
    "bad",
    [
        {"max_attempts": 0},
        {"failure_threshold": 0},
        {"base_delay": -1.0},
        {"max_delay": 0.5},          # base_delay(1.0) 보다 작음
        {"cooldown": -1.0},
    ],
    ids=["max_attempts", "failure_threshold", "base_delay", "max_delay", "cooldown"],
)
def test_ac19_rejects_invalid_configuration(bad):
    with pytest.raises(ValueError):
        make(**bad)
