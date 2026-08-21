"""이 실험이 측정하는 모델 특성과, 그 특성이 결정하는 하네스 손잡이 (ADR-001c).

코어는 스키마와 렌더만 갖는다. 매핑은 **여기** 있다 — 무엇이 무엇을 함의하는지는 도메인
지식이고, 다음 실험은 다른 손잡이를 들고 올 것이기 때문이다.

등급은 필수다. 아래 규칙 중 일부는 두 모델에서 재현됐고(***), 일부는 한 번 봤으며(**),
일부는 순전히 판단이다(*). 이 구분을 지우면 의견이 권고로 세탁된다.
"""
from __future__ import annotations

from ...core.ledger.profile import Rule

# 측정할 특성. `tier` 는 **어느 티어가 이것을 잴 수 있는가** 이다.
#
# tier-1(계약이 오라클)은 두 개를 원리적으로 못 잰다:
#   finds_per_call   "진짜 결함" 을 세려면 판정된 결함 집합이 필요한데, tier-1 의 v0 는
#                    검증된 정답(19/19)이라 판정할 결함이 없다.
#   verbosity_shift  리포 접근 유무의 대비인데, tier-1 은 단일 파일 과제라 리포가 없다.
#
# 못 재는 것을 0 이나 추정으로 채우지 않는다. None 으로 두면 그 특성에 걸린 규칙은
# 발화하지 않고(Profile.prescribe 가 KeyError 를 삼킨다), 프로파일에 무엇이 비었는지 남는다.
TRAIT_KEYS = {
    "spread":            ("tier-1", "같은 코드를 N회 리뷰했을 때 지적 수의 범위 (max-min)"),
    "loop_decay":        ("tier-1", "루프 라운드가 갈수록 지적이 주는가 (선형 기울기)"),
    "churn_dries":       ("tier-1", "churn 후반부 평균이 전반부의 0.7 미만인가 (4점 이상일 때만)"),
    "churn_ratio":       ("tier-1", "churn 후반부 평균 / 전반부 평균"),
    "rejection_rate":    ("tier-1", "수정자로 썼을 때 지적을 거절하는 비율"),
    "malformed_rate":    ("tier-1", "JSON 강제에도 파싱 불가한 응답 비율"),
    "ac_held":           ("tier-1", "루프 전 라운드에서 계약 준수가 유지됐는가"),
    "loc_direction":     ("tier-1", "루프 종료 시 LOC / 시작 LOC. >1 늘림, <1 줄임"),
    "tools_blockable":   ("adapter", "이 어댑터로 도구를 끌 수 있는가"),
    "finds_per_call":    ("tier-2", "리포 접근 조건에서 콜당 잡은 '진짜' 결함 수"),
    "verbosity_shift":   ("tier-2", "리포를 열었을 때 원시 지적 수 변화율 (음수=말을 아낌)"),
}

RULES: list[Rule] = [
    Rule("fanout", lambda v: v["finds_per_call"] < 2.0,
         "카테고리 팬아웃을 붙여라 (예산 3배를 쓸 수 있을 때만)", "**",
         "콜당 발견이 낮다 — 단독 리뷰가 저빈도 결함을 잘라낸다"),

    # ★ 등급 격하 (D-001 해소). 원래 ***(두 모델 재현) 이었으나 두 가지 이유로 ** 다:
    #   1) 3루프 판정이 갈림 1:2 — 만장일치가 아니다
    #   2) codex 는 None (D-002) — 이 특성은 **두 모델에서 재현될 수 없고**, 따라서
    #      ***("두 모델 이상에서 재현")의 정의를 만족할 방법이 구조적으로 없다
    Rule("round_cap", lambda v: v["churn_dries"] is False,
         "라운드 상한을 반드시 걸어라", "**",
         "churn 이 마르지 않는다 — 정지 기준이 스스로 발화하지 않는다 (D-001)"),

    Rule("churn_gate", lambda v: v["churn_dries"] is False,
         "churn 수렴을 정지 기준으로 쓰지 마라", "**",
         "3루프 판정 1:2. churn_ratio 연속값을 같이 읽어라 — 문턱 0.7 이 "
         "이 과제에서는 분포 한복판이다 (D-001)"),

    Rule("churn_gate", lambda v: v["churn_dries"] is True,
         "churn 수렴을 정지 기준으로 쓸 수 있다", "**",
         "이 모델은 라운드가 갈수록 수정 폭이 줄어든다"),

    Rule("churn_gate", lambda v: v["churn_dries"] is None,
         "churn 정지 기준을 쓸 근거가 없다 — 라운드 상한을 걸어라", "*",
         "루프가 너무 일찍 끝나 계열이 짧다. 마르는지 잴 수 없는 것이지 "
         "마르지 않는 것이 아니다 (D-002)"),

    # ★ 새 규칙 — 두 모델에서 각각 확인됐고 원 연구와도 일치한다
    Rule("loop_budget", lambda v: v["loc_direction"] > 1.15,
         "루프를 짧게 끊어라 — 이 모델은 라운드마다 코드를 불린다", "***",
         "loc_direction > 1.15. 원 연구에서도 claude 는 +24~152%, "
         "codex 는 -12% 로 방향이 갈렸다"),

    Rule("loop_budget", lambda v: v["loc_direction"] < 1.0,
         "루프를 더 돌려도 코드가 커지지 않는다", "***",
         "loc_direction < 1.0 — 이 모델은 반영하면서 코드를 줄인다"),

    Rule("triage_load", lambda v: v["verbosity_shift"] > 0,
         "사람 선별 부담을 크게 잡아라 — 리포를 주면 말이 는다", "**",
         "리포 접근이 이 모델에서는 지적 수를 늘린다"),

    Rule("triage_load", lambda v: v["verbosity_shift"] < -0.3,
         "사람 선별 부담은 작다 — 대신 놓치는 것을 의심해라", "**",
         "리포 접근이 지적을 절반 이하로 줄인다. 아끼는 쪽이 놓친다"),

    Rule("repetition", lambda v: v["spread"] >= 3,
         "한 번으로 끝내지 마라 — 회차별 편차가 크다", "***",
         "같은 코드에 대한 지적 수가 회차마다 크게 흔들린다"),

    Rule("as_fixer", lambda v: v["rejection_rate"] > 0.45,
         "수정자로 쓰려면 계약 문서를 반드시 같이 줘라", "**",
         "거절률이 높다 — 확인할 문서 없이 '범위 고정' 만 들으면 애매한 것을 다 거절한다"),

    Rule("json_contract", lambda v: v["malformed_rate"] > 0.05,
         "JSON 강제를 믿지 말고 파싱 실패를 정상 경로로 다뤄라", "**",
         "구조화 출력 지시에도 파싱 불가 응답이 나온다"),

    Rule("comparability", lambda v: v["tools_blockable"] is False,
         "차단 가능한 모델과 같은 표에 올리지 마라 — 조건이 다르다", "*",
         "도구를 끌 수 없다. 이 벤치의 최대 미해결이며 판단이지 측정이 아니다"),
]
