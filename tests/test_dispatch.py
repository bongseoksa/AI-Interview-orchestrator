"""지시 채팅 디스패처 자가검증 — 실행: python tests/test_dispatch.py

LLM 호출 없음(라우터는 스텁). 노션 호출 없음(확인함은 파일만).
"""

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gui import dispatch as D
from src.gui import review as R

PASS = []


def check(name, fn):
    fn()
    PASS.append(name)
    print(f"  ok  {name}")


# ── 1. 문서 명명 (07 §6) ──

def t_slug():
    assert D.slugify("M1 서비스 LLM 선정") == "M1-서비스-LLM-선정"
    assert "_" not in D.slugify("a_b/c:d"), "구분자 '_'와 경로문자는 제거돼야 한다"
    assert D.slugify("") == "무제"
    assert len(D.slugify("가" * 100)) == 40, "어절 경계가 없으면 그냥 자른다"


def t_trim_at_word_boundary():
    # 노션 페이지 제목이 되므로 어절 중간에서 끊기면 안 된다
    src = "Phase 5 M1 착수 전 서버 레포에 필요한 최소 테스트/배포 준비가 뭔지 짧게 정리해줘"
    t = D.trim(src)
    assert len(t) <= 40 and not t.endswith(("-", " ")), t
    assert src.startswith(t) and src[len(t)] in " -", f"어절 중간 절단: {t!r}"
    # route와 slugify가 같은 절단을 쓴다 — 이중 절단으로 어긋나면 안 된다
    agenda = D.route(f"@qa-engineer {src}", llm_call=None)["agenda"]
    assert D.slugify(agenda) == D.slugify(D.trim(src)), "route/slugify 절단 불일치"


def t_doc_name():
    n = D.doc_name("2026-08-07", "M1 서비스 LLM 선정", "회의록")
    assert n == "2026-08-07_M1-서비스-LLM-선정_회의록", n
    assert n.count("_") == 2, "필드 구분자는 정확히 2개"
    taken = {n}
    n2 = D.doc_name("2026-08-07", "M1 서비스 LLM 선정", "회의록", taken)
    assert n2 == n + "_2", n2
    taken.add(n2)
    assert D.doc_name("2026-08-07", "M1 서비스 LLM 선정", "회의록", taken).endswith("_3")


# ── 2. 라우팅 3단 폴백 (07 §4) ──

def t_mention():
    valid = set(D._catalog())
    assert "fullstack-architect" in valid
    got = D.parse_mentions("@fullstack-architect @qa-engineer @없는놈 봐줘", valid)
    assert got == ["fullstack-architect", "qa-engineer"], got


def t_route_mention_skips_llm():
    def boom(_):
        raise AssertionError("@멘션이 있으면 LLM을 호출하면 안 된다")
    r = D.route("@qa-engineer 테스트 전략 짜줘", llm_call=boom)
    assert r["agents"] == ["qa-engineer"]
    assert "@" not in r["agenda"] and "테스트 전략" in r["agenda"], r["agenda"]


def t_route_llm():
    stub = lambda _: '설명 어쩌고 {"agents":["product-manager","infra-expert"],"agenda":"M1 LLM 선정","ask":null} 끝'
    r = D.route("M1 서비스 LLM 정해줘", llm_call=stub)
    assert r["agents"] == ["product-manager", "infra-expert"], r
    assert r["ask"] is None


def t_route_filters():
    # 서기는 자동 참석이므로 제외, 없는 id도 제외
    stub = lambda _: json.dumps({"agents": ["doc-secretary", "없는놈", "qa-engineer"], "agenda": "x"})
    assert D.route("...", llm_call=stub)["agents"] == ["qa-engineer"]


def t_route_fallback_asks():
    for stub in (lambda _: "JSON 아님",
                 lambda _: json.dumps({"agents": [], "ask": "누구에게 시킬까요?"})):
        r = D.route("음", llm_call=stub)
        assert r["agents"] == [] and r["ask"], r
    # 라우터 예외도 실행 대신 되묻기로 떨어져야 한다
    def boom(_):
        raise RuntimeError("ollama down")
    assert D.route("음", llm_call=boom)["ask"]


# ── 3. Crew 조립 — 참석자 수가 곧 모드 (07 §5) ──

def t_solo_is_not_meeting():
    crew, is_meeting = D.build_crew(["qa-engineer"], "테스트 전략")
    assert is_meeting is False
    assert len(crew.agents) == 1 and len(crew.tasks) == 1
    roles = " ".join(a.role for a in crew.agents)
    assert "서기" not in roles, "1명이면 서기 Task를 붙이지 않는다"


def t_meeting_appends_secretary():
    ids = ["product-manager", "fullstack-architect", "infra-expert"]
    crew, is_meeting = D.build_crew(ids, "M1 서비스 LLM 선정")
    assert is_meeting is True
    assert len(crew.agents) == 4 and len(crew.tasks) == 4, (len(crew.agents), len(crew.tasks))
    cat = D._catalog()
    assert [a.role for a in crew.agents[:3]] == [cat[i]["role"] for i in ids], "참석자 순서 유지"
    assert "서기" in crew.agents[-1].role
    assert len(crew.tasks[-1].context) == 3, "서기 Task는 앞 발언 전부를 context로 받는다"


def t_bad_ids():
    try:
        D.build_crew(["없는놈"], "x")
    except ValueError:
        return
    raise AssertionError("유효 에이전트 0명이면 ValueError")


# ── 4. 회의록 조립 — LLM 없이 원문 무절단 (D8) ──

def t_transcript():
    long_text = "가" * 3000

    class Out:
        def __init__(self, raw):
            self.raw = raw
            self.agent = None

    class Result:
        tasks_output = [Out(long_text), Out("두번째")]

    md = D.build_transcript("M1 선정", ["product-manager", "infra-expert"], Result())
    assert "# M1 선정" in md and "## 발언 전문" in md
    assert long_text in md, "저장은 무절단 (D8)"
    assert "프로덕트 매니저" in md and "인프라" in md


# ── 5. 확인함 왕복 (07 §7) ──

def t_review_roundtrip():
    tmp = R.PROJECT_ROOT / "output" / "_review_test"
    doc_dir = R.PROJECT_ROOT / "output" / "_meetings_test"
    orig = R.REVIEW_DIR
    R.REVIEW_DIR = tmp
    try:
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(doc_dir, ignore_errors=True)
        doc_dir.mkdir(parents=True)
        f = doc_dir / "2026-08-07_테스트_회의록.md"
        f.write_text("본문", encoding="utf-8")

        assert R.pending() == []
        R.enqueue("run1", "테스트", "2026-08-07",
                  [{"kind": "회의록", "title": f.stem, "path": str(f)}])
        assert len(R.pending()) == 1
        assert R.preview("run1")["docs"][0]["content"] == "본문"
        assert R.preview("없는run")["error"]

        assert R.reject("run1")["ok"] is True
        assert R.pending() == [] and not f.exists(), "반려는 초안 md도 지운다"
    finally:
        R.REVIEW_DIR = orig
        shutil.rmtree(tmp, ignore_errors=True)
        shutil.rmtree(doc_dir, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in [(k[2:], v) for k, v in sorted(globals().items()) if k.startswith("t_")]:
        check(name, fn)
    print(f"\n{len(PASS)} passed")
