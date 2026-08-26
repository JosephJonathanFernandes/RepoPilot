import json
import os

def normalize_command(command):
    if not command:
        return None
    c = command.strip().lower()
    c = c.replace('./.', '.')
    c = c.replace(' /', ' ')
    return c

def normalize_framework(fw):
    if not fw:
        return None
    return fw.strip().lower()

def match_architecture(actual, expected):
    if actual == expected:
        return True
    if actual and expected:
        return actual.lower() in expected.lower() or expected.lower() in actual.lower()
    return False

def grade_entry_point(actual_ep, actual_evidence, expected_ep, expected_evidence):
    # Both actual and expected are dicts with 'answer' and 'evidence'
    # Actually, RepoPilot returns multiple entry points, we usually pick the highest confidence one.
    pass

def grade_run_command(actual_cmd, actual_source, expected_cmd):
    if not actual_cmd and not expected_cmd:
        return True
    return normalize_command(actual_cmd) == normalize_command(expected_cmd)

def grade_framework(actual_fw, expected_fw):
    if not actual_fw and not expected_fw:
        return True
    return normalize_framework(actual_fw) == normalize_framework(expected_fw)
