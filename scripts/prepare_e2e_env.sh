#!/usr/bin/env bash
# 로컬 E1 실연동용 .env 생성 (git에 커밋되지 않음)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
EXAMPLE="$ROOT/.env.github.example"
SANDBOX_REPO="${E2E_SANDBOX_REPO:-Legas-park/ai-agent-core-e2e-sandbox}"

if [[ -f "$ENV_FILE" ]]; then
  echo "이미 .env 가 있습니다: $ENV_FILE"
  echo "덮어쓰려면: rm .env && $0"
  exit 0
fi

if [[ ! -f "$EXAMPLE" ]]; then
  echo "템플릿 없음: $EXAMPLE"
  exit 1
fi

SECRET="$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")"

cp "$EXAMPLE" "$ENV_FILE"

# macOS / Linux sed
if sed --version >/dev/null 2>&1; then
  SED=(sed -i)
else
  SED=(sed -i '')
fi

"${SED[@]}" "s|^WEBHOOK_SECRET=.*|WEBHOOK_SECRET=$SECRET|" "$ENV_FILE"
"${SED[@]}" "s|^GITHUB_DEFAULT_REPO=.*|GITHUB_DEFAULT_REPO=$SANDBOX_REPO|" "$ENV_FILE"

echo "생성됨: $ENV_FILE (gitignore 대상)"
echo ""
echo "=== 아래 3가지만 .env 에 직접 입력하세요 ==="
echo "  GITHUB_ACCESS_TOKEN=   (PAT: repo 또는 PR read/write)"
echo "  GEMINI_API_KEY=        (또는 다른 LLM 공급자)"
echo "  GEMINI_MODEL=          (공급자 문서의 model id)"
echo ""
echo "WEBHOOK_SECRET (GitHub Webhook Secret 에 동일하게):"
echo "  $SECRET"
echo ""
echo "Sandbox repo (webhook·테스트 PR 전용):"
echo "  https://github.com/$SANDBOX_REPO"
echo ""
echo "다음: docs/setup/e2e-sandbox.md"
