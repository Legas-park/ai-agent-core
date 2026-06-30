#!/usr/bin/env python3
"""
GitHub pull_request webhook 을 로컬 /webhook/gateway 로 전송합니다.
ngrok 없이 플러그인 라우팅·서명 검증을 확인할 때 사용합니다.

사용 예:
  WEBHOOK_SECRET=my-secret python3 scripts/simulate_github_pr_webhook.py
  WEBHOOK_SECRET=my-secret python3 scripts/simulate_github_pr_webhook.py --repo Legas-park/ai-agent-core --pr 9
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request


def _build_payload(repo: str, pr_number: int, action: str) -> dict:
    return {
        "action": action,
        "pull_request": {
            "number": pr_number,
            "title": "test: E1 webhook simulation",
            "head": {"ref": "feat/e1-test"},
        },
        "repository": {"full_name": repo},
    }


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def main() -> int:
    parser = argparse.ArgumentParser(description="GitHub PR webhook 시뮬레이터")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="앱 base URL")
    parser.add_argument("--repo", default="Legas-park/ai-agent-core", help="owner/repo")
    parser.add_argument("--pr", type=int, default=1, help="PR 번호")
    parser.add_argument("--action", default="opened", help="GitHub action")
    args = parser.parse_args()

    secret = os.environ.get("WEBHOOK_SECRET", "")
    payload = _build_payload(args.repo, args.pr, args.action)
    body = json.dumps(payload).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Hub-Signature-256"] = _sign(body, secret)

    url = f"{args.base_url.rstrip('/')}/webhook/gateway"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            print(f"HTTP {resp.status}")
            print(text)
            return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"연결 실패: {exc.reason}", file=sys.stderr)
        print("서버가 실행 중인지 확인: python3 -m uvicorn main:app --host 0.0.0.0 --port 8000", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
