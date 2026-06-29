# 기여 가이드

AI Agent Core에 기여해 주셔서 감사합니다. 이 문서는 브랜치, 커밋, PR, 테스트 방법을 정리합니다.

## 시작하기

```bash
git clone https://github.com/Legas-park/ai-agent-core.git
cd ai-agent-core
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
pytest tests/ -v
```

## 브랜치 규칙

- `main` — 안정 브랜치 (직접 커밋 금지)
- 기능: `feat/설명-YYYYMMDD-HHMMSS`
- 수정: `fix/설명-YYYYMMDD-HHMMSS`
- 문서: `docs/설명-YYYYMMDD-HHMMSS`

## 커밋 메시지

[Conventional Commits](https://www.conventionalcommits.org/) 형식을 사용합니다.

```
feat: LLM fallback router 추가
fix: webhook 서명 검증 오류 수정
docs: installation guide 추가
test: setup API 통합 테스트
chore: requirements 버전 핀
```

## Pull Request

1. `main`에서 기능 브랜치 생성
2. 변경 + 테스트 추가/수정
3. `pytest tests/ -v` 통과 확인
4. PR 설명에 **무엇을 / 왜** 변경했는지 작성
5. 관련 이슈가 있으면 `#123` 형식으로 링크

## 코드 스타일

- Python 3.9+
- 기존 패키지 구조·네이밍 유지 (`core/`, `services/plugins/`)
- 코어(`core/`)는 도메인 무지 — 비즈니스 로직은 플러그인에
- 주석·docstring은 한국어 가능

## 테스트

```bash
pytest tests/ -v
```

새 기능에는 가능하면 테스트를 포함해 주세요. CI(GitHub Actions)에서 동일하게 실행됩니다.

## 보안

API 키·토큰을 코드나 PR에 포함하지 마세요. `.env`는 커밋하지 않습니다. 자세한 내용은 [SECURITY.md](SECURITY.md)를 참고하세요.

## 질문

버그·기능 제안은 GitHub Issues를 이용해 주세요.
