# -*- coding: utf-8 -*-
"""LLM 연결 지점 (기본: 꺼짐 → 규칙 기반으로 동작).

지금 앱은 '에이전트인 척' 하는 시연판이라 LLM 없이 규칙·템플릿으로 답한다.
실제 LLM(사내 sLLM, 상용 API 등)을 붙일 때는 아래 두 함수만 채우면 된다.
  - classify_voc(text)  → dict(cat, label, conf, severity, entities, owner, scores, engine="llm") 또는 None
  - persona_voice(...)  → str 또는 None
None을 돌려주면 호출한 쪽이 규칙 기반 결과를 쓴다."""


def available() -> bool:
    return False


def classify_voc(text: str):
    return None


def persona_voice(persona: dict, context: dict):
    return None
