"""code_review 플러그인 전용 프롬프트 템플릿 모음."""

SYSTEM_PROMPT = """당신은 깐깐하지만 공정한 시니어 소프트웨어 엔지니어입니다.
GitLab Merge Request의 변경 디프(diff)를 리뷰하여 실제로 가치 있는 지적만 남깁니다.
스타일 취향이나 사소한 포매팅은 무시하고, 버그·보안 취약점·성능 문제·명백한 설계 결함에 집중하세요.
확신이 없으면 지적하지 마세요. 노이즈보다 정확도가 중요합니다.
반드시 지정된 JSON 스키마로만 응답하세요."""

REVIEW_PROMPT_TEMPLATE = """다음은 Merge Request "{title}" (소스 브랜치: {source_branch})의 변경 디프입니다.
각 파일의 추가/삭제 라인을 검토하고 문제를 찾아주세요.

=== 변경 디프 시작 ===
{diff_block}
=== 변경 디프 끝 ===

아래 JSON 스키마로만 응답하세요. 다른 텍스트는 출력하지 마세요.
{{
  "summary": "이 MR에 대한 2~3문장 한국어 총평",
  "issues": [
    {{
      "file": "문제가 있는 파일 경로",
      "severity": "critical | major | minor",
      "category": "bug | security | performance | design | other",
      "comment": "무엇이 왜 문제인지, 어떻게 고치면 좋은지 한국어로 구체적으로"
    }}
  ]
}}

지적할 문제가 없으면 issues를 빈 배열로 두세요."""


def build_review_prompt(title: str, source_branch: str, diff_block: str) -> str:
    return REVIEW_PROMPT_TEMPLATE.format(
        title=title or "(제목 없음)",
        source_branch=source_branch or "(unknown)",
        diff_block=diff_block,
    )


def render_review_comment(summary: str, issues: list) -> str:
    """LLM 리뷰 결과를 GitLab MR에 붙일 마크다운 코멘트로 렌더링합니다."""
    severity_icon = {"critical": "🔴", "major": "🟠", "minor": "🟡"}
    lines = ["## 🤖 AI 코드 리뷰", "", summary or "_총평 없음_", ""]
    if not issues:
        lines.append("✅ 특별히 막아야 할 이슈는 발견하지 못했습니다.")
        return "\n".join(lines)

    lines.append(f"### 발견된 이슈 {len(issues)}건")
    lines.append("")
    for it in issues:
        icon = severity_icon.get(str(it.get("severity", "")).lower(), "⚪")
        file = it.get("file", "(unknown)")
        category = it.get("category", "other")
        comment = it.get("comment", "")
        lines.append(f"- {icon} **`{file}`** _({category})_  ")
        lines.append(f"  {comment}")
    lines.append("")
    lines.append("> 본 코멘트는 AI Agent Core가 자동 생성했습니다. 최종 판단은 리뷰어가 합니다.")
    return "\n".join(lines)
