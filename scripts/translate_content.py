"""DB 콘텐츠 번역 파이프라인 — gemma4:12b (Tier 2) 로컬 번역

Supabase의 nodes/questions 테이블 원문(ko)을 영어로 번역하여
node_translations/question_translations 테이블에 저장한다.

사용법:
  source .venv/bin/activate
  python scripts/translate_content.py                # 전체 번역
  python scripts/translate_content.py --dry-run      # 미리보기만
  python scripts/translate_content.py --limit 5      # 5개만 테스트
"""

import argparse
import json
import os
import sys
import time
import urllib.request

# Supabase 설정 (.env.local에서 읽기)
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma4:12b"
TARGET_LOCALE = "en"


def load_env():
    """AI-Interview-web/.env.local에서 환경변수 로드"""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "AI-Interview-web", ".env.local"
    )
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())
    global SUPABASE_URL, SUPABASE_KEY
    SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", SUPABASE_URL)
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY)


def supabase_request(method: str, path: str, data=None) -> dict:
    """Supabase REST API 호출"""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def ollama_generate(prompt: str) -> str:
    """Ollama API로 텍스트 생성"""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 2048},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read())
    return result.get("response", "").strip()


def translate_text(text: str, context: str = "") -> str:
    """한국어 텍스트를 영어로 번역"""
    if not text or not text.strip():
        return ""
    prompt = f"""Translate the following Korean text to English.
This is technical content about frontend engineering interview preparation.
Keep technical terms (React, Next.js, TypeScript, etc.) as-is.
Translate naturally and accurately. Output ONLY the English translation, nothing else.

{f"Context: {context}" if context else ""}

Korean text:
{text}

English translation:"""
    return ollama_generate(prompt)


def translate_keywords(keywords: list[str]) -> list[str]:
    """키워드 배열 번역"""
    if not keywords:
        return []
    prompt = f"""Translate these Korean technical keywords to English.
Keep technical terms as-is. Output ONLY a JSON array of English strings.

Korean keywords: {json.dumps(keywords, ensure_ascii=False)}

English keywords (JSON array):"""
    result = ollama_generate(prompt)
    try:
        # JSON 배열 추출
        start = result.find("[")
        end = result.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except json.JSONDecodeError:
        pass
    # 파싱 실패 시 원본 반환
    return keywords


def get_existing_translations(table: str, id_col: str) -> set[str]:
    """이미 번역된 ID 목록 조회"""
    try:
        path = f"{table}?locale=eq.{TARGET_LOCALE}&select={id_col}"
        data = supabase_request("GET", path)
        return {row[id_col] for row in data}
    except Exception:
        return set()


def translate_nodes(dry_run: bool = False, limit: int | None = None):
    """nodes 테이블 번역"""
    print("\n=== 노드 번역 시작 ===")

    # 모든 노드 조회
    nodes = supabase_request("GET", "nodes?is_active=eq.true&select=id,title,content_body,key_keywords,default_tip,category")
    print(f"총 {len(nodes)}개 노드")

    # 이미 번역된 노드 제외
    existing = get_existing_translations("node_translations", "node_id")
    remaining = [n for n in nodes if n["id"] not in existing]
    print(f"이미 번역됨: {len(existing)}개, 남은 번역: {len(remaining)}개")

    if limit:
        remaining = remaining[:limit]

    for i, node in enumerate(remaining):
        print(f"\n[{i+1}/{len(remaining)}] {node['title'][:50]}...")

        if dry_run:
            print(f"  (dry-run) 건너뜀")
            continue

        try:
            title_en = translate_text(node["title"], f"Category: {node['category']}")
            content_en = translate_text(node.get("content_body") or "", f"Topic: {node['title']}")
            keywords_en = translate_keywords(node.get("key_keywords") or [])
            tip_en = translate_text(node.get("default_tip") or "", f"Interview tip for: {node['title']}")

            translation = {
                "node_id": node["id"],
                "locale": TARGET_LOCALE,
                "title": title_en,
                "content_body": content_en or None,
                "key_keywords": keywords_en or None,
                "default_tip": tip_en or None,
            }

            supabase_request("POST", "node_translations", translation)
            print(f"  ✓ {title_en[:60]}")

            time.sleep(0.5)  # Ollama 부하 조절

        except Exception as e:
            print(f"  ✗ 에러: {e}")
            continue


def translate_questions(dry_run: bool = False, limit: int | None = None):
    """questions 테이블 번역"""
    print("\n=== 질문 번역 시작 ===")

    questions = supabase_request("GET", "questions?select=id,question,answer_guide,node_id")
    print(f"총 {len(questions)}개 질문")

    existing = get_existing_translations("question_translations", "question_id")
    remaining = [q for q in questions if q["id"] not in existing]
    print(f"이미 번역됨: {len(existing)}개, 남은 번역: {len(remaining)}개")

    if limit:
        remaining = remaining[:limit]

    for i, q in enumerate(remaining):
        print(f"\n[{i+1}/{len(remaining)}] {q['question'][:50]}...")

        if dry_run:
            print(f"  (dry-run) 건너뜀")
            continue

        try:
            question_en = translate_text(q["question"], "Frontend interview diagnostic question")
            guide_en = translate_text(q.get("answer_guide") or "", f"Answer guide for: {q['question']}")

            translation = {
                "question_id": q["id"],
                "locale": TARGET_LOCALE,
                "question": question_en,
                "answer_guide": guide_en or None,
            }

            supabase_request("POST", "question_translations", translation)
            print(f"  ✓ {question_en[:60]}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  ✗ 에러: {e}")
            continue


def main():
    parser = argparse.ArgumentParser(description="DB 콘텐츠 번역 파이프라인")
    parser.add_argument("--dry-run", action="store_true", help="번역 없이 대상만 확인")
    parser.add_argument("--limit", type=int, help="번역할 최대 항목 수")
    parser.add_argument("--nodes-only", action="store_true", help="노드만 번역")
    parser.add_argument("--questions-only", action="store_true", help="질문만 번역")
    args = parser.parse_args()

    load_env()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("에러: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 환경변수 필요")
        print("AI-Interview-web/.env.local에서 자동 로드하거나 환경변수로 설정하세요.")
        sys.exit(1)

    print("=" * 60)
    print("DB 콘텐츠 번역 파이프라인")
    print(f"모델: {MODEL} (Tier 2 — 로컬)")
    print(f"대상 언어: {TARGET_LOCALE}")
    print(f"Dry-run: {args.dry_run}")
    print("=" * 60)

    if not args.questions_only:
        translate_nodes(dry_run=args.dry_run, limit=args.limit)

    if not args.nodes_only:
        translate_questions(dry_run=args.dry_run, limit=args.limit)

    print("\n" + "=" * 60)
    print("번역 파이프라인 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
