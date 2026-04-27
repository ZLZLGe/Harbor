#!/usr/bin/env python3
import json
from pathlib import Path

import requests

ANSWER_DIR = Path("/root/answer")
GATEWAY = "http://127.0.0.1:8765"


def fetch_json(path):
    response = requests.get(f"{GATEWAY}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


def fetch_text(path):
    response = requests.get(f"{GATEWAY}{path}", timeout=5)
    response.raise_for_status()
    return response.text


def main():
    ANSWER_DIR.mkdir(parents=True, exist_ok=True)
    papers = fetch_json("/papers")["papers"]
    by_key = {paper["canonical_key"]: paper for paper in papers}
    accepted_keys = [
        "lewis2020rag",
        "guu2020realm",
        "karpukhin2020dpr",
        "izacard2021fid",
        "gao2023hyde",
    ]

    references = "\n".join(fetch_text(f"/bibtex/{key}").strip() for key in accepted_keys) + "\n"
    (ANSWER_DIR / "references.bib").write_text(references, encoding="utf-8")

    rejected = [
        {"input_key_or_title": "lewis2020rag_duplicate", "reason": "duplicate"},
        {"input_key_or_title": "chen2024universalragcure", "reason": "fake_or_unverified"},
        {"input_key_or_title": "smith2022qa", "reason": "fake_or_unverified"},
        {"input_key_or_title": "broken_source", "reason": "malformed"},
        {"input_key_or_title": "singhal2023medpalm", "reason": "outside_scope"},
        {"input_key_or_title": "vaswani2017attention", "reason": "outside_scope"},
    ]

    matrix = {
        "claims": [
            {
                "claim_id": "C01",
                "decision": "supported",
                "corrected_claim": None,
                "evidence_keys": ["lewis2020rag"],
                "rationale": "Lewis et al. describe RAG as combining parametric seq2seq generation with retrieved non-parametric memory and evaluate it on knowledge-intensive NLP tasks.",
            },
            {
                "claim_id": "C02",
                "decision": "supported",
                "corrected_claim": None,
                "evidence_keys": ["guu2020realm"],
                "rationale": "REALM augments language-model pre-training with a latent document retriever and reports open-domain QA gains.",
            },
            {
                "claim_id": "C03",
                "decision": "supported",
                "corrected_claim": None,
                "evidence_keys": ["karpukhin2020dpr"],
                "rationale": "DPR uses separate dense encoders for questions and passages as an alternative to sparse lexical retrieval for open-domain QA.",
            },
            {
                "claim_id": "C04",
                "decision": "wrong_citation",
                "corrected_claim": "Fusion-in-Decoder studies how retrieved passages can be fused in a generative model for open-domain question answering; it does not establish clinical safety standards.",
                "evidence_keys": ["izacard2021fid"],
                "rationale": "The FiD evidence concerns open-domain QA architecture and passage fusion, not clinical safety evaluation.",
            },
            {
                "claim_id": "C05",
                "decision": "overstated",
                "corrected_claim": "HyDE proposes hypothetical document generation for zero-shot dense retrieval without relevance labels, but the evidence does not show that labels are unnecessary in every retrieval domain.",
                "evidence_keys": ["gao2023hyde"],
                "rationale": "The paper supports zero-shot dense retrieval benefits, while domain-universal elimination of labels is broader than the evidence.",
            },
            {
                "claim_id": "C06",
                "decision": "overstated",
                "corrected_claim": "Adding retrieval can improve factual grounding and knowledge access, but the accepted evidence does not show that retrieval fully solves hallucination.",
                "evidence_keys": ["lewis2020rag", "izacard2021fid", "gao2023hyde"],
                "rationale": "The accepted evidence shows retrieval can improve knowledge access and QA performance, but it still leaves faithfulness and failed-retrieval risks unresolved.",
            },
            {
                "claim_id": "C07",
                "decision": "out_of_scope",
                "corrected_claim": None,
                "evidence_keys": [],
                "rationale": "The Med-PaLM record is a clinical knowledge evaluation paper, not an in-scope RAG architecture paper for open-domain QA.",
            },
            {
                "claim_id": "C08",
                "decision": "unsupported",
                "corrected_claim": None,
                "evidence_keys": accepted_keys,
                "rationale": "The accepted packet is dominated by model, retrieval, and benchmark evaluations; the gateway metadata does not show that all accepted studies report human-participant experiments.",
            },
            {
                "claim_id": "C09",
                "decision": "wrong_citation",
                "corrected_claim": "Dense Passage Retrieval uses supervised dense retrieval training, while HyDE targets zero-shot dense retrieval without relevance labels; they do not make the same supervision assumption.",
                "evidence_keys": ["karpukhin2020dpr", "gao2023hyde"],
                "rationale": "The DPR evidence notes supervised training data, whereas HyDE explicitly targets zero-shot retrieval without relevance labels.",
            },
            {
                "claim_id": "C10",
                "decision": "supported",
                "corrected_claim": None,
                "evidence_keys": ["guu2020realm"],
                "rationale": "The REALM record states that retrieved documents are treated as latent variables during retrieval-augmented language-model pre-training.",
            },
            {
                "claim_id": "C11",
                "decision": "out_of_scope",
                "corrected_claim": None,
                "evidence_keys": [],
                "rationale": "The Transformer paper is important background for modern NLP but the gateway marks it outside the packet scope because it does not study retrieval-augmented or open-domain QA retrieval architecture.",
            },
            {
                "claim_id": "C12",
                "decision": "overstated",
                "corrected_claim": "Fusion-in-Decoder studies how retrieved passages are fused for generative open-domain QA, but retrieval coverage remains a methodological limitation.",
                "evidence_keys": ["izacard2021fid"],
                "rationale": "The FiD evidence supports passage fusion and generative QA evaluation, while its limitations still include dependence on retrieval coverage.",
            },
        ],
        "source_assessments": [
            {
                "bib_key": "lewis2020rag",
                "research_design": "retrieval-augmented sequence-to-sequence generation evaluated on knowledge-intensive NLP and open-domain QA tasks",
                "main_contribution": "Introduces RAG as a core architecture combining parametric generation with retrieved non-parametric memory.",
                "methodological_limitations": ["retrieval quality affects generation", "faithfulness is improved but not guaranteed"],
                "scope_role": "core_architecture",
                "human_participants": False,
            },
            {
                "bib_key": "guu2020realm",
                "research_design": "retrieval-augmented language-model pre-training with latent document retrieval",
                "main_contribution": "Shows how retrieval can be integrated into pre-training and fine-tuning for open-domain QA.",
                "methodological_limitations": ["retrieval corpus design shapes results", "pre-training choices affect downstream gains"],
                "scope_role": "core_architecture",
                "human_participants": False,
            },
            {
                "bib_key": "karpukhin2020dpr",
                "research_design": "supervised dual-encoder dense passage retrieval for open-domain question answering",
                "main_contribution": "Provides the dense retrieval baseline and retrieval-side mechanism used by later RAG-style systems.",
                "methodological_limitations": ["requires supervised training data", "retrieval performance varies by dataset"],
                "scope_role": "retrieval_method",
                "human_participants": False,
            },
            {
                "bib_key": "izacard2021fid",
                "research_design": "retrieval-conditioned encoder-decoder generation with decoder-side fusion of passages",
                "main_contribution": "Demonstrates a generation-side passage fusion strategy for open-domain QA.",
                "methodological_limitations": ["depends on retrieval coverage", "not a clinical evaluation paper"],
                "scope_role": "generation_method",
                "human_participants": False,
            },
            {
                "bib_key": "gao2023hyde",
                "research_design": "hypothetical-document generation for zero-shot dense retrieval without relevance labels",
                "main_contribution": "Extends the retrieval side by using generated hypothetical documents to support zero-shot dense retrieval.",
                "methodological_limitations": ["domain generalization remains empirical", "generation quality affects retrieval"],
                "scope_role": "retrieval_method",
                "human_participants": False,
            },
        ],
        "rejected_sources": rejected,
    }
    (ANSWER_DIR / "evidence_matrix.json").write_text(json.dumps(matrix, indent=2), encoding="utf-8")

    titles = {key: by_key[key]["title"] for key in accepted_keys}
    note = f"""## Research Question

What does the core scholarly evidence show about retrieval-augmented language models for open-domain question answering, and what limitations remain?

## Evidence Synthesis

The accepted evidence shows a progression from dense retrieval to retrieval-conditioned generation. RAG combines retrieved non-parametric memory with a parametric generator for knowledge-intensive NLP tasks [lewis2020rag]. REALM brings retrieval into language-model pre-training by treating retrieved documents as latent evidence [guu2020realm]. DPR focuses on the retrieval stage, using dual encoders as an alternative to sparse lexical retrieval for open-domain QA [karpukhin2020dpr]. FiD then emphasizes how multiple retrieved passages can be fused inside a generative reader for open-domain QA [izacard2021fid]. HyDE extends the retrieval side by generating hypothetical documents for zero-shot dense retrieval without relevance labels [gao2023hyde].

## Methodological Caveats

The evidence is mostly benchmark-driven and depends on retrieval corpus quality, retrieval coverage, and dataset choice. Retrieval-side limitations include supervised-data requirements for DPR and empirical domain-transfer limits for HyDE [karpukhin2020dpr] [gao2023hyde]. Generation-side limitations include FiD's dependence on the retrieved passages it receives and RAG's remaining faithfulness risks [izacard2021fid] [lewis2020rag]. Evaluation-side limitations include reliance on open-domain QA benchmarks rather than human-participant studies or clinical safety protocols.

## Research Gaps

Remaining gaps include stronger faithfulness measurement, clearer domain-transfer evidence, better treatment of failed retrieval, and evaluation protocols that separate retrieval errors from generator errors.

## References

- [lewis2020rag] {titles["lewis2020rag"]}.
- [guu2020realm] {titles["guu2020realm"]}.
- [karpukhin2020dpr] {titles["karpukhin2020dpr"]}.
- [izacard2021fid] {titles["izacard2021fid"]}.
- [gao2023hyde] {titles["gao2023hyde"]}.
"""
    (ANSWER_DIR / "literature_note.md").write_text(note, encoding="utf-8")


if __name__ == "__main__":
    main()
