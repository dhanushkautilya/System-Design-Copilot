from __future__ import annotations

import math
from typing import Dict, List


def calc_qps(dau: int, peak_concurrency: int, read_write_ratio: float, burst_factor: float = 1.5) -> Dict[str, float]:
    base_qps = max(dau * 0.1 / 86400, peak_concurrency / 10)  # heuristic
    peak_qps = base_qps * burst_factor
    read_qps = peak_qps * (read_write_ratio / (1 + read_write_ratio))
    write_qps = peak_qps - read_qps
    return {
        "base_qps": round(base_qps, 2),
        "peak_qps": round(peak_qps, 2),
        "read_qps": round(read_qps, 2),
        "write_qps": round(write_qps, 2),
    }


def calc_storage(records_per_user: int, avg_record_size_kb: float, retention_days: int, dau: int) -> Dict[str, float]:
    daily_gb = dau * records_per_user * avg_record_size_kb / 1024 / 1024
    total_gb = daily_gb * retention_days
    monthly_growth_gb = daily_gb * 30
    return {
        "daily_gb": round(daily_gb, 3),
        "total_gb_retention": round(total_gb, 3),
        "monthly_growth_gb": round(monthly_growth_gb, 3),
    }


def generate_mermaid_flow(components: List[str], flows: List[str]) -> str:
    lines = ["flowchart TD"]
    for comp in components:
        lines.append(f"  {comp}")
    for flow in flows:
        lines.append(f"  {flow}")
    return "\n".join(lines)


def generate_mermaid_components(components: List[str]) -> str:
    lines = ["graph LR"]
    for comp in components:
        lines.append(f"  {comp}")
    return "\n".join(lines)


def risk_checklist(compliance_flags: List[str], data_types: List[str]) -> List[str]:
    risks = []
    if any(flag.upper() in {"HIPAA", "PHI"} for flag in compliance_flags + data_types):
        risks.append("PHI present: require HIPAA controls, BAA, access logging")
    if any(flag.upper() in {"PCI", "CARD"} for flag in compliance_flags + data_types):
        risks.append("PCI data: segment card data environment, tokenization, yearly SAQ")
    if any(flag.upper() == "PII" for flag in data_types):
        risks.append("PII present: need data minimization, DSR workflows, encryption at rest")
    if not risks:
        risks.append("Standard web-app risks: OWASP Top 10, SSRF, IDOR, rate limiting")
    return risks
