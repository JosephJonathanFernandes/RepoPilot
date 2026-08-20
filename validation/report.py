import json
from pathlib import Path
from typing import List
import dataclasses
from validation.models import ValidationReport

class DataclassEncoder(json.JSONEncoder):
    def default(self, obj):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        return super().default(obj)

def generate_report(report: ValidationReport, output_dir: Path):
    json_path = output_dir / "latest.json"
    json_path.write_text(json.dumps(report, cls=DataclassEncoder, indent=2), encoding='utf-8')
    
    md = [
        "RepoPilot Validation Report",
        "===========================\n",
        f"Repositories evaluated: {report.repositories_evaluated}\n",
        "Scanner",
        "-------",
    ]
    for r, data in report.scanner_results.items():
        md.append(f"**{r}**:")
        for k, v in data.items():
            md.append(f"- {k}: {v}")
        md.append("")
        
    md.extend([
        "Facts",
        "-----"
    ])
    for r, data in report.facts_results.items():
        md.append(f"**{r}**:")
        for k, v in data.items():
            md.append(f"- {k}: {v}")
        md.append("")
        
    md.extend([
        "Entry Points",
        "------------"
    ])
    for r, data in report.entrypoints_results.items():
        md.append(f"**{r}**:")
        for k, v in data.items():
            md.append(f"- {k}: {v}")
        md.append("")
        
    md.extend([
        "Architecture",
        "------------"
    ])
    for r, data in report.architecture_results.items():
        md.append(f"**{r}**:")
        for k, v in data.items():
            md.append(f"- {k}: {v}")
        md.append("")
        
    md.extend([
        "False Positives",
        "---------------"
    ])
    if report.false_positives:
        for fp in report.false_positives:
            md.append(f"- {fp}")
    else:
        md.append("None detected.")
    md.append("")
        
    md.extend([
        "False Negatives",
        "---------------"
    ])
    if report.false_negatives:
        for fn in report.false_negatives:
            md.append(f"- {fn}")
    else:
        md.append("None detected.")
    md.append("")
        
    md.extend([
        "Confidence Audit",
        "----------------",
        f"HIGH-confidence correct: {report.confidence_audit.high_correct}",
        f"HIGH-confidence incorrect: {report.confidence_audit.high_incorrect}",
        "",
        f"MEDIUM-confidence correct: {report.confidence_audit.medium_correct}",
        f"MEDIUM-confidence incorrect: {report.confidence_audit.medium_incorrect}",
        ""
    ])
    
    md.extend([
        "Overall Findings",
        "----------------"
    ])
    for f in report.findings:
        md.append(f"- {f}")
        
    md_path = output_dir / "latest.md"
    md_path.write_text("\n".join(md), encoding='utf-8')
