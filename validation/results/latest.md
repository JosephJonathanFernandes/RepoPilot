RepoPilot Validation Report
===========================

Repositories evaluated: 7

Scanner
-------
Facts
-----
**fastapi_app**:
- Languages Recall: 1/1
- Frameworks Recall: 1/1

**go_app**:
- Languages Recall: 1/1

**large_repo**:
- Languages Recall: 1/1

**monorepo**:

**node_app**:
- Languages Recall: 1/1

**python_cli**:
- Languages Recall: 1/1

**react_app**:
- Languages Recall: 1/1
- Frameworks Recall: 1/1

Entry Points
------------
**fastapi_app**:

**go_app**:

**large_repo**:

**monorepo**:

**node_app**:

**python_cli**:

**react_app**:

Architecture
------------
**fastapi_app**:

**go_app**:

**large_repo**:

**monorepo**:

**node_app**:

**python_cli**:

**react_app**:

False Positives
---------------
- [monorepo] False architecture pattern: Backend/API application
- [node_app] False entry points: {'package.json'}
- [node_app] False architecture pattern: Layered

False Negatives
---------------
- [fastapi_app] Missed architecture pattern: {'MVC-like'}
- [python_cli] Missed architecture pattern: {'Flat / Script-based'}

Confidence Audit
----------------
HIGH-confidence correct: 5
HIGH-confidence incorrect: 1

MEDIUM-confidence correct: 7
MEDIUM-confidence incorrect: 2

Overall Findings
----------------
- [large_repo] Scanner successfully ignored large directories.