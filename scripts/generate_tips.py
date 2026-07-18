"""M6: Default Tip 생성 — gemma4:26b (Tier 1) 로컬 모델로 면접 팁 생성

Supabase nodes 테이블의 default_tip을 실질적인 면접 팁으로 업그레이드한다.
현재 "핵심 키워드: X, Y, Z" 수준 → "면접에서 이렇게 답하세요" 수준으로 개선.

사용법:
  source .venv/bin/activate
  python scripts/generate_tips.py                # 전체 생성
  python scripts/generate_tips.py --dry-run      # 미리보기만
  python scripts/generate_tips.py --limit 5      # 5개만 테스트
"""

import argparse
import json
import os
import sys
import urllib.request

SUPABASE_URL = ""
SUPABASE_KEY = ""
OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma4:26b"


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
    SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


def supabase_get(path: str):
    """Supabase REST API GET"""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def supabase_patch(table: str, node_id: str, data: dict):
    """Supabase REST API PATCH"""
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{node_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def ollama_generate(prompt: str) -> str:
    """Ollama Chat API로 텍스트 생성 (think:false — thinking 모드 비활성화)"""
    url = f"{OLLAMA_URL}/api/chat"
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "think": False,
        "options": {"temperature": 0.4, "num_predict": 300},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    chunks = []
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            if line.strip():
                token = json.loads(line)
                content = token.get("message", {}).get("content", "")
                if content:
                    chunks.append(content)
                if token.get("done"):
                    break
    return "".join(chunks).strip()


def generate_tip(title: str, content_body: str, key_keywords: list) -> str:
    """노드 정보를 기반으로 면접 팁 생성"""
    keywords_str = ", ".join(key_keywords[:5]) if key_keywords else ""
    content_preview = (content_body or "")[:500]

    prompt = f"""당신은 프론트엔드 기술 면접 코치입니다.
아래 개념에 대한 면접 팁을 2~3문장으로 작성하세요.

요구사항:
- 면접에서 이 개념을 질문받았을 때 어떻게 답변해야 하는지 구체적 조언
- "~하세요" 체로 작성
- 핵심 키워드를 자연스럽게 포함
- 실무 경험과 연결하는 방법 언급
- 반드시 한국어로 작성
- 팁 내용만 출력 (제목, 번호, 불릿 없이)

개념: {title}
핵심 키워드: {keywords_str}
내용 요약: {content_preview}

면접 팁:"""

    return ollama_generate(prompt)


def main():
    parser = argparse.ArgumentParser(description="M6: Default Tip 생성")
    parser.add_argument("--dry-run", action="store_true", help="미리보기만")
    parser.add_argument("--limit", type=int, default=0, help="처리할 노드 수 제한")
    args = parser.parse_args()

    load_env()
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Supabase 환경변수가 설정되지 않았습니다.")
        print("  AI-Interview-web/.env.local에 SUPABASE_SERVICE_ROLE_KEY 필요")
        sys.exit(1)

    # 전체 노드 가져오기
    path = "nodes?select=id,title,content_body,key_keywords,default_tip&is_active=eq.true&order=category,difficulty"
    if args.limit > 0:
        path += f"&limit={args.limit}"
    nodes = supabase_get(path)
    print(f"대상 노드: {len(nodes)}개")

    success = 0
    fail = 0

    for i, node in enumerate(nodes):
        title = node["title"]
        print(f"\n[{i+1}/{len(nodes)}] {title[:50]}...")

        try:
            tip = generate_tip(
                title,
                node.get("content_body", ""),
                node.get("key_keywords", []),
            )
        except Exception as e:
            print(f"  ERROR (생성 실패): {e}")
            fail += 1
            continue

        if not tip or len(tip) < 20:
            print(f"  SKIP (팁이 너무 짧음): {tip}")
            fail += 1
            continue

        # 불필요한 prefix 정리
        for prefix in ["면접 팁:", "팁:", "답변:"]:
            if tip.startswith(prefix):
                tip = tip[len(prefix):].strip()

        print(f"  TIP: {tip[:80]}...")

        if not args.dry_run:
            try:
                supabase_patch("nodes", node["id"], {"default_tip": tip})
                print(f"  DB 업데이트 완료")
                success += 1
            except Exception as e:
                print(f"  ERROR (DB 업데이트 실패): {e}")
                fail += 1
        else:
            success += 1

    print(f"\n{'='*60}")
    print(f"결과: 성공 {success} / 실패 {fail} / 전체 {len(nodes)}")
    if args.dry_run:
        print("(--dry-run 모드: DB 변경 없음)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
