"""참조 구현 — 인수 테스트 검증 전용. 실험 대상 에이전트에게는 절대 노출되지 않는다.

존재 이유: 한 번도 실행되지 않은 테스트 스위트는 오라클이 될 수 없다. 만족 불가능하거나
자체 버그가 있으면 실험은 아무것도 재지 못한다. 이 파일은 SPEC-retry-policy.md 만 보고
작성되었고, 테스트가 실제로 통과 가능한지 확인하는 데만 쓴다.

실험 실행 시 이 디렉터리는 샌드박스 scratch 에 복사되지 않는다.
"""

from __future__ import annotations


class CircuitOpenError(Exception):
    """회로가 열려 있어 호출이 차단됨."""


class RetryPolicy:
    def __init__(
        self,
        max_attempts: int,
        base_delay: float,
        max_delay: float,
        retryable: tuple,
        failure_threshold: int,
        cooldown: float,
        time_fn,
        sleep_fn,
        rand_fn,
    ):
        # AC-19
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if base_delay < 0:
            raise ValueError("base_delay must be >= 0")
        if max_delay < base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if cooldown < 0:
            raise ValueError("cooldown must be >= 0")

        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._retryable = retryable
        self._failure_threshold = failure_threshold
        self._cooldown = cooldown
        self._time = time_fn
        self._sleep = sleep_fn
        self._rand = rand_fn

        self._consecutive_failures = 0
        self._opened_at: float | None = None
        self._state = "closed"
        self._trial_in_flight = False

    @property
    def state(self) -> str:
        return self._state

    # ---------------------------------------------------------------- 내부

    def _delay_for(self, retry_index: int) -> float:
        """retry_index 는 1부터. AC-06 상한 적용 후 AC-07 지터를 곱한다."""
        capped = min(self._base_delay * (2 ** (retry_index - 1)), self._max_delay)
        return self._rand() * capped

    def _on_failure(self) -> None:
        """AC-09: call 단위로 1 증가. AC-15: half-open 실패는 즉시 재개방."""
        if self._state == "half_open":
            self._state = "open"
            self._opened_at = self._time()
            self._consecutive_failures += 1
            return
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._state = "open"
            self._opened_at = self._time()

    def _on_success(self) -> None:
        # AC-12 / AC-14
        self._consecutive_failures = 0
        self._state = "closed"
        self._opened_at = None

    def _admit(self) -> None:
        """게이트. 통과하지 못하면 CircuitOpenError (AC-11/13/16/18)."""
        if self._state == "closed":
            return
        if self._state == "half_open":
            # AC-16: 시험 호출은 하나만
            raise CircuitOpenError("half-open trial already in flight")
        # open
        assert self._opened_at is not None
        if self._time() - self._opened_at >= self._cooldown:
            self._state = "half_open"   # AC-13: fn 호출 시점의 state
            return
        raise CircuitOpenError("circuit is open")

    # ---------------------------------------------------------------- 공개

    def call(self, fn, *args, **kwargs):
        self._admit()   # AC-18: 여기서 던지면 실패로 세지 않는다

        was_half_open = self._state == "half_open"
        if was_half_open:
            self._trial_in_flight = True

        try:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    result = fn(*args, **kwargs)
                except self._retryable as exc:
                    if attempt == self._max_attempts:
                        self._on_failure()          # AC-09
                        raise
                    # AC-04: 마지막 시도 뒤에는 잠들지 않는다
                    self._sleep(self._delay_for(attempt))
                    del exc
                except BaseException:
                    self._on_failure()              # AC-05 + AC-17
                    raise
                else:
                    self._on_success()
                    return result
        finally:
            if was_half_open:
                self._trial_in_flight = False
