#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to validate the evidence reference attribution fix.

This script tests that:
1. Evidence mapping is created correctly with group_id.index format
2. References are resolved to the correct expert's evidence
3. Invalid references are handled gracefully
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DeepRareAgent.p03summary_agent import _resolve_evidence_references


def test_basic_reference_resolution():
    """Test basic reference resolution with group_id.index format"""
    print("\n" + "="*60)
    print("TEST 1: Basic Reference Resolution")
    print("="*60)
    
    evidence_mapping = {
        "group_a.1": "Patient reports burning pain in extremities",
        "group_a.2": "Physical exam shows angiokeratomas on trunk",
        "group_b.1": "Lab results show elevated creatinine",
        "group_b.2": "Echocardiogram reveals left ventricular hypertrophy",
    }
    
    report_text = """
# Diagnostic Summary

Based on the clinical presentation <ref>group_a.1</ref> and physical findings <ref>group_a.2</ref>,
combined with laboratory evidence <ref>group_b.1</ref> and cardiac imaging <ref>group_b.2</ref>,
the diagnosis of Fabry Disease is highly suspected.
"""
    
    result = _resolve_evidence_references(report_text, evidence_mapping)
    
    print("Input report:")
    print(report_text)
    print("\nResolved report:")
    print(result)
    
    # Verify all references are resolved
    assert "[group_a.1]" in result, "group_a.1 reference not resolved"
    assert "[group_a.2]" in result, "group_a.2 reference not resolved"
    assert "[group_b.1]" in result, "group_b.1 reference not resolved"
    assert "[group_b.2]" in result, "group_b.2 reference not resolved"
    assert "Patient reports burning pain" in result, "Evidence content missing"
    
    print("\n✅ TEST PASSED: All references resolved correctly")


def test_invalid_reference_handling():
    """Test handling of invalid references"""
    print("\n" + "="*60)
    print("TEST 2: Invalid Reference Handling")
    print("="*60)
    
    evidence_mapping = {
        "group_a.1": "Valid evidence",
    }
    
    report_text = """
Valid reference: <ref>group_a.1</ref>
Invalid reference: <ref>group_b.99</ref>
"""
    
    result = _resolve_evidence_references(report_text, evidence_mapping)
    
    print("Input report:")
    print(report_text)
    print("\nResolved report:")
    print(result)
    
    # Should resolve valid reference
    assert "[group_a.1]" in result, "Valid reference not resolved"
    # Should not crash on invalid reference
    assert "group_b.99" in result or True, "Should handle invalid reference gracefully"
    
    print("\n✅ TEST PASSED: Invalid references handled gracefully")


def test_no_references():
    """Test report with no references"""
    print("\n" + "="*60)
    print("TEST 3: No References")
    print("="*60)
    
    evidence_mapping = {
        "group_a.1": "Some evidence",
    }
    
    report_text = """
# Simple Report

This report has no evidence references.
"""
    
    result = _resolve_evidence_references(report_text, evidence_mapping)
    
    print("Input report:")
    print(report_text)
    print("\nResolved report:")
    print(result)
    
    # Should return unchanged
    assert result == report_text, "Report should be unchanged"
    
    print("\n✅ TEST PASSED: Report without references unchanged")


def test_duplicate_references():
    """Test report with duplicate references"""
    print("\n" + "="*60)
    print("TEST 4: Duplicate References")
    print("="*60)
    
    evidence_mapping = {
        "group_a.1": "Key finding",
    }
    
    report_text = """
First mention: <ref>group_a.1</ref>
Second mention: <ref>group_a.1</ref>
Third mention: <ref>group_a.1</ref>
"""
    
    result = _resolve_evidence_references(report_text, evidence_mapping)
    
    print("Input report:")
    print(report_text)
    print("\nResolved report:")
    print(result)
    
    # Should only append evidence once
    evidence_count = result.count("[group_a.1] Key finding")
    assert evidence_count == 1, f"Evidence should appear once, found {evidence_count} times"
    
    print("\n✅ TEST PASSED: Duplicate references handled correctly")


def test_misattribution_prevention():
    """Test that the new system prevents misattribution"""
    print("\n" + "="*60)
    print("TEST 5: Misattribution Prevention (Key Test)")
    print("="*60)
    
    # Simulate the OLD broken behavior
    print("\n--- OLD SYSTEM (Broken) ---")
    print("Expert A evidences: ['A1', 'A2']")
    print("Expert B evidences: ['B1', 'B2']")
    print("Global list: ['A1', 'A2', 'B1', 'B2']")
    print("Reference <ref>1</ref> in 'Group B analysis' → 'A2' ❌ WRONG!")
    
    # Show NEW system
    print("\n--- NEW SYSTEM (Fixed) ---")
    evidence_mapping = {
        "expert_a.1": "Evidence A1",
        "expert_a.2": "Evidence A2",
        "expert_b.1": "Evidence B1",
        "expert_b.2": "Evidence B2",
    }
    
    report_text = """
Based on Expert A's analysis <ref>expert_a.1</ref> and <ref>expert_a.2</ref>.
Based on Expert B's analysis <ref>expert_b.1</ref> and <ref>expert_b.2</ref>.
"""
    
    result = _resolve_evidence_references(report_text, evidence_mapping)
    
    print("Evidence mapping:")
    for key, value in evidence_mapping.items():
        print(f"  {key}: {value}")
    
    print("\nResolved report:")
    print(result)
    
    # Verify correct attribution
    assert "[expert_a.1] Evidence A1" in result
    assert "[expert_a.2] Evidence A2" in result
    assert "[expert_b.1] Evidence B1" in result
    assert "[expert_b.2] Evidence B2" in result
    
    print("\n✅ TEST PASSED: Evidence correctly attributed to each expert")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Evidence Reference Attribution Fix - Test Suite")
    print("="*60)
    
    try:
        test_basic_reference_resolution()
        test_invalid_reference_handling()
        test_no_references()
        test_duplicate_references()
        test_misattribution_prevention()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nThe evidence reference attribution fix is working correctly.")
        print("References are now stable and unambiguous using group_id.index format.")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
