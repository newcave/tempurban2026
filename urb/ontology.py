# -*- coding: utf-8 -*-
"""도시개발 전주기 온톨로지 v0 (시연용 초안) — 클래스·관계·인과 경로·ISO/IEC 5087-1 대응 후보."""
import networkx as nx

CLASSES = {
    # id: (한글, 그룹, 설명)
    "Project": ("사업", "공간", "도시개발사업 단위"),
    "Site": ("사업지", "공간", "부산EDC · 김포 · 송산GC · 시화MTV"),
    "Zone": ("생활권", "공간", "학교·교통·상권을 공유하는 생활 단위"),
    "Block": ("개발블록", "공간", "공동주택·상업 블록"),
    "Phase": ("공정", "공정", "부지조성 · 기반시설 · 건축 · 분양 · 입주"),
    "Milestone": ("마일스톤", "공정", "착공 · 준공 · 개교 · 개통"),
    "Facility": ("기반시설", "공급", "학교 · 도로·교량 · 상가·의료 · 공원"),
    "Service": ("생활서비스", "공급", "통학 · 통근 · 생활편의 · 여가"),
    "Household": ("가구·인구", "수요", "입주 세대, 학생 수"),
    "Persona": ("주민 Agent 유형", "수요", "영유아 · 학령기 · 통근 · 고령 · 1인 · 상가"),
    "Gap": ("공급-수요 갭", "인과", "수용력 대비 부족률"),
    "Inconvenience": ("생활불편", "인과", "Agent 유형 가중 체감 불편"),
    "VOC": ("VOC(민원)", "인과", "유형 · 채널 · 심각도 · 처리상태"),
    "Indicator": ("지표", "평가", "접근성 · 생활불편지수 · VOC 위험등급 · 비용 · 공정영향"),
    "Lever": ("대안 레버", "평가", "학교 조기공급 · 교통 선투자 · 임시대책 · 물량조정"),
    "Organization": ("주체", "평가", "K-water · 지자체 · 교육청 · 시공사"),
}
# 화면 배치 (왼쪽 → 오른쪽: 공간 → 공정·수요 → 공급 → 인과 → 평가)
LAYOUT = {"Project": (0, 3.2), "Site": (0, 2.2), "Zone": (0, 1.2), "Block": (0, 0.2),
          "Phase": (1, 2.9), "Milestone": (1.9, 3.4), "Household": (1, 0.0), "Persona": (1, -1.0),
          "Facility": (2.2, 2.3), "Service": (2.6, 1.3),
          "Gap": (3.3, 0.9), "Inconvenience": (3.3, -0.2), "VOC": (4.3, -0.2),
          "Lever": (3.6, 2.9), "Indicator": (5.2, 0.9), "Organization": (5.2, 2.3)}
GROUP_COLORS = {"공간": "#a78bfa", "공정": "#f59e0b", "공급": "#22d3ee", "수요": "#f472b6", "인과": "#f87171", "평가": "#34d399"}

RELATIONS = [
    ("Project", "Site", "hasSite"), ("Site", "Zone", "hasZone"), ("Zone", "Block", "hasBlock"),
    ("Block", "Phase", "undergoes"), ("Phase", "Milestone", "reaches"), ("Milestone", "Facility", "delivers"),
    ("Facility", "Service", "provides"), ("Block", "Household", "accommodates"), ("Household", "Persona", "typedAs"),
    ("Service", "Gap", "suppliesTo"), ("Household", "Gap", "demands"), ("Gap", "Inconvenience", "causes"),
    ("Persona", "Inconvenience", "perceives"), ("Inconvenience", "VOC", "expressedAs"), ("Phase", "Inconvenience", "disturbs"),
    ("VOC", "Indicator", "measuredBy"), ("Inconvenience", "Indicator", "measuredBy"),
    ("Lever", "Milestone", "shifts"), ("Lever", "Service", "supplements"), ("Lever", "Block", "reschedules"),
    ("Lever", "Organization", "ownedBy"), ("Lever", "Indicator", "costs"), ("VOC", "Organization", "routedTo"),
]

# 인과 경로 (연구 핵심 질문 ②: 공정·분양·입주·기반시설·생활불편·VOC의 인과경로)
CAUSAL_PATHS = [
    ["공정 지연", "개교·개통 지연", "공급-수요 갭↑", "생활불편↑", "VOC↑"],
    ["분양·입주 속도↑", "가구 수요↑", "공급-수요 갭↑", "생활불편↑", "VOC↑"],
    ["인접 블록 공사", "소음·분진·통학 위험", "생활불편↑", "VOC↑"],
    ["VOC 확산(이웃·커뮤니티)", "집단 민원", "사업 이미지·분양률↓", "사업성↓"],
]

# ISO/IEC 5087-1 (City data model — foundation level) 대응 후보 — 검토용, 확정 아님
ISO5087 = [
    ("Site · Zone · Block", "공간 위치(Spatial Location) 계열", "생활권·블록 경계를 공간 객체로"),
    ("Phase · Milestone", "활동(Activity) · 시간(Time) 계열", "공정을 시작·종료가 있는 활동으로"),
    ("Facility · Service", "자원(Resource) 계열", "수용력(정원·노선 수용 세대)을 자원 속성으로"),
    ("Household · Persona", "사람·가구(Person/Household) 계열", "개인정보 없이 유형·구성비만"),
    ("Organization", "조직(Organization) 계열", "레버 주체 · VOC 처리 부서"),
    ("Indicator", "측정·단위(Quantity/Units) 계열", "지표 단위·산식 명시"),
    ("Gap · Inconvenience · VOC", "변화(Change) 계열 + 확장", "표준에 직접 대응 없음 → K-water 확장 클래스"),
]


def graph() -> nx.DiGraph:
    g = nx.DiGraph()
    for k, (ko, grp, desc) in CLASSES.items():
        g.add_node(k, ko=ko, group=grp, desc=desc)
    for a, b, r in RELATIONS:
        g.add_edge(a, b, rel=r)
    return g


def resolve(zone_name: str, entities=()) -> list:
    """질문·VOC를 온톨로지 노드에 붙이는 흉내 (에이전트 트레이스용)."""
    out = [f"Zone:{zone_name}"]
    out += [e for e in entities]
    return out
