def calculate_accuracy(actual, expected):
    """Calculates strict accuracy."""
    if not expected:
        return actual is None
    if not actual:
        return False
    return actual == expected

def calculate_escr_ucr(claims, expected_evidence):
    """
    Calculates Evidence-Supported Claim Rate (ESCR) and Unsupported Claim Rate (UCR).
    claims: list of dicts: {'claim': 'FastAPI', 'evidence': 'pyproject.toml'}
    expected_evidence: list of dicts indicating ground truth evidence.
    """
    if not claims:
        return 0.0, 0.0
        
    supported = 0
    unsupported = 0
    
    for c in claims:
        # Simplistic matching for now
        # A claim is supported if its evidence is physically correct and aligns with ground truth
        if c.get("supported", False):
            supported += 1
        else:
            unsupported += 1
            
    total = supported + unsupported
    return supported / total, unsupported / total

def calculate_abstention_rate(answers, total_questions):
    if not total_questions:
        return 0.0
    abstained = sum(1 for a in answers if a is None)
    return abstained / total_questions
