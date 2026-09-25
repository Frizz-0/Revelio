from app.investigator.models import Evidence
from app.investigator.verifier import EvidenceVerifier


evidence = [
    Evidence(
        source="https://example.com/source-a",
        title="Source A",
        url="https://example.com/source-a",
        claim="NVIDIA holds 80% of the AI accelerator market by revenue in 2025.",
        supporting_text=(
            "NVIDIA holds 80% of the AI accelerator market by revenue in 2025."
        ),
        relevance=1.0,
        evidence_type="reported_statistic",
    ),

    Evidence(
        source="https://example.com/source-b",
        title="Source B",
        url="https://example.com/source-b",
        claim="NVIDIA holds 20% of the AI accelerator market by revenue in 2025.",
        supporting_text=(
            "NVIDIA holds 20% of the AI accelerator market by revenue in 2025."
        ),
        relevance=1.0,
        evidence_type="reported_statistic",
    ),
]


sub_question = "What is NVIDIA's current AI GPU market share?"


verifier = EvidenceVerifier()

finding = verifier.verify(
    sub_question=sub_question,
    evidence=evidence,
)


print("\n=== VERIFIED FINDING ===")
print("=" * 60)

print(f"\nSub-question:")
print(finding.sub_question)

print(f"\nStatus:")
print(finding.status)

print(f"\nConclusion:")
print(finding.conclusion)

print(f"\nSupporting evidence:")
for evidence_id in finding.supporting_evidence:
    print(f"  - Evidence {evidence_id}")

print(f"\nContradicting evidence:")
for evidence_id in finding.contradicting_evidence:
    print(f"  - Evidence {evidence_id}")

print(f"\nCaveats:")
for caveat in finding.caveats:
    print(f"  - {caveat}")