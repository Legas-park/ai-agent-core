#!/usr/bin/env python3
"""GET /health 를 호출해 연동 준비 상태를 확인합니다."""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--strict", action="store_true", help="configured 항목이 false면 exit 1")
    args = parser.parse_args()

    url = f"{args.base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        print(f"health 확인 실패: {exc.reason}", file=sys.stderr)
        return 1

    print(json.dumps(data, indent=2, ensure_ascii=False))

    if not args.strict:
        return 0

    ok = data.get("repository_configured") and data.get("llm_configured")
    if not ok:
        print("\nstrict 검증 실패: repository_configured 또는 llm_configured 가 false 입니다.", file=sys.stderr)
        print(f"  missing repository: {data.get('repository_missing_fields')}", file=sys.stderr)
        print(f"  missing llm: {data.get('llm_missing_fields')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
