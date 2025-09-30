#!/usr/bin/env python3
"""
Test script for the optimized TGE monitoring system
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main_optimized import OptimizedCryptoTGEMonitor
from config import COMPANIES, HIGH_CONFIDENCE_TGE_KEYWORDS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_matching_logic():
    """Test the enhanced matching logic with sample TGE announcements."""
    logger.info("Testing enhanced matching logic...")
    
    monitor = OptimizedCryptoTGEMonitor()
    
    # Test cases with expected outcomes
    test_cases = [
        {
            "content": "Exciting news! Caldera is launching their TGE next week. The $CAL token will be available for trading on major exchanges.",
            "expected_relevant": True,
            "expected_companies": ["Caldera"],
            "min_confidence": 0.6
        },
        {
            "content": "Fhenix Protocol announces the launch of their native token $FHE. Token generation event scheduled for this Friday.",
            "expected_relevant": True,
            "expected_companies": ["Fhenix"],
            "min_confidence": 0.7
        },
        {
            "content": "Succinct Labs is proud to announce the upcoming TGE for their innovative SP1 token. Airdrop details coming soon!",
            "expected_relevant": True,
            "expected_companies": ["Succinct"],
            "min_confidence": 0.7
        },
        {
            "content": "Curvance Finance mainnet is now live! Trading for $CURV tokens starts tomorrow on all major DEXs.",
            "expected_relevant": True,
            "expected_companies": ["Curvance"],
            "min_confidence": 0.6
        },
        {
            "content": "Bitcoin price analysis shows potential for growth this quarter.",
            "expected_relevant": False,
            "expected_companies": [],
            "min_confidence": 0.0
        },
        {
            "content": "General crypto market update: Ethereum gas fees remain high.",
            "expected_relevant": False,
            "expected_companies": [],
            "min_confidence": 0.0
        }
    ]
    
    passed = 0
    total = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\nTest Case {i}: {test_case['content'][:50]}...")
        
        is_relevant, confidence, analysis = monitor.enhanced_content_analysis(
            test_case['content'], 
            "test"
        )
        
        # Check results
        passed_test = True
        
        if is_relevant != test_case['expected_relevant']:
            logger.error(f"  ❌ Relevance mismatch: got {is_relevant}, expected {test_case['expected_relevant']}")
            passed_test = False
        
        if confidence < test_case['min_confidence']:
            logger.error(f"  ❌ Confidence too low: got {confidence:.0%}, expected >={test_case['min_confidence']:.0%}")
            passed_test = False
        
        for expected_company in test_case['expected_companies']:
            if expected_company not in analysis['matched_companies']:
                logger.error(f"  ❌ Missing company: {expected_company}")
                passed_test = False
        
        if passed_test:
            logger.info(f"  ✅ PASSED - Confidence: {confidence:.0%}")
            passed += 1
        else:
            logger.info(f"  ❌ FAILED")
        
        # Show analysis details
        logger.info(f"     Companies: {analysis['matched_companies']}")
        logger.info(f"     Keywords: {analysis['matched_keywords'][:3]}")
        logger.info(f"     Strategies: {analysis['strategy']}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Matching Logic Test Results: {passed}/{total} passed ({passed/total:.0%})")
    
    return passed == total


def test_deduplication():
    """Test content deduplication functionality."""
    logger.info("\nTesting deduplication...")
    
    monitor = OptimizedCryptoTGEMonitor()
    
    # Test exact duplicate
    content1 = "Caldera TGE announced for next week!"
    url1 = "https://example.com/caldera-tge"
    
    # First occurrence should be unique
    is_unique1 = monitor.deduplicate_content(content1, url1)
    logger.info(f"First occurrence unique: {is_unique1}")
    
    # Second occurrence should be duplicate
    is_unique2 = monitor.deduplicate_content(content1, url1)
    logger.info(f"Second occurrence unique: {is_unique2}")
    
    # Similar content test
    content2 = "Caldera announces TGE for next week!"
    is_unique3 = monitor.deduplicate_content(content2)
    logger.info(f"Similar content unique: {is_unique3}")
    
    success = is_unique1 and not is_unique2 and not is_unique3
    logger.info(f"Deduplication test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


def test_company_prioritization():
    """Test company priority handling."""
    logger.info("\nTesting company prioritization...")
    
    monitor = OptimizedCryptoTGEMonitor()
    
    # High priority company test
    high_priority_content = "Caldera launches mainnet next week"
    is_relevant_high, conf_high, analysis_high = monitor.enhanced_content_analysis(high_priority_content, "test")
    
    # Low priority company test  
    low_priority_content = "Espresso launches mainnet next week"
    is_relevant_low, conf_low, analysis_low = monitor.enhanced_content_analysis(low_priority_content, "test")
    
    logger.info(f"High priority confidence: {conf_high:.0%}")
    logger.info(f"Low priority confidence: {conf_low:.0%}")
    
    # High priority should have higher confidence for similar content
    success = conf_high >= conf_low
    logger.info(f"Priority test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


def test_token_symbol_detection():
    """Test token symbol pattern matching."""
    logger.info("\nTesting token symbol detection...")
    
    monitor = OptimizedCryptoTGEMonitor()
    
    test_content = "The $CAL token from Caldera will start trading tomorrow. Also $FHE from Fhenix is launching."
    is_relevant, confidence, analysis = monitor.enhanced_content_analysis(test_content, "test")
    
    expected_symbols = ["$CAL", "$FHE"]
    found_symbols = analysis.get('token_symbols', [])
    
    symbols_found = all(symbol in found_symbols for symbol in expected_symbols)
    companies_matched = len(analysis.get('matched_companies', [])) >= 2
    
    success = symbols_found and companies_matched and confidence > 0.6
    
    logger.info(f"Found symbols: {found_symbols}")
    logger.info(f"Matched companies: {analysis.get('matched_companies', [])}")
    logger.info(f"Confidence: {confidence:.0%}")
    logger.info(f"Symbol detection test: {'✅ PASSED' if success else '❌ FAILED'}")
    
    return success


def test_exclusion_patterns():
    """Test exclusion pattern functionality."""
    logger.info("\nTesting exclusion patterns...")
    
    monitor = OptimizedCryptoTGEMonitor()
    
    # Content that should be excluded
    exclusion_tests = [
        "Caldera testnet token launch for developers",
        "Fhenix game token drop for players",
        "Technical analysis of Succinct token price"
    ]
    
    passed = 0
    total = len(exclusion_tests)
    
    for content in exclusion_tests:
        is_relevant, confidence, analysis = monitor.enhanced_content_analysis(content, "test")
        
        # Should have reduced confidence due to exclusions
        has_exclusions = len(analysis.get('exclusions', [])) > 0 or confidence < 0.4
        
        if has_exclusions:
            passed += 1
            logger.info(f"  ✅ Excluded: {content[:40]}...")
        else:
            logger.info(f"  ❌ Not excluded: {content[:40]}...")
    
    success = passed >= total * 0.7  # At least 70% should be excluded
    logger.info(f"Exclusion test: {passed}/{total} excluded ({'✅ PASSED' if success else '❌ FAILED'})")
    
    return success


def run_performance_test():
    """Test system performance with sample data."""
    logger.info("\nRunning performance test...")
    
    try:
        monitor = OptimizedCryptoTGEMonitor()
        
        # Test with multiple pieces of content
        test_contents = [
            "Caldera TGE announced for Q1 2024",
            "Fhenix Protocol launches $FHE token next week",
            "Bitcoin price reaches new highs",
            "Succinct Labs announces SP1 token distribution",
            "Ethereum gas fees remain stable",
            "Curvance mainnet goes live with $CURV trading",
            "DeFi sector sees continued growth",
            "Fabric Protocol reveals tokenomics for upcoming TGE"
        ]
        
        import time
        start_time = time.time()
        
        relevant_count = 0
        for content in test_contents:
            is_relevant, confidence, analysis = monitor.enhanced_content_analysis(content, "test")
            if is_relevant:
                relevant_count += 1
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Processed {len(test_contents)} items in {processing_time:.3f}s")
        logger.info(f"Average time per item: {processing_time/len(test_contents):.3f}s")
        logger.info(f"Relevant items found: {relevant_count}/{len(test_contents)}")
        
        # Performance should be under 0.1s per item
        success = processing_time / len(test_contents) < 0.1
        logger.info(f"Performance test: {'✅ PASSED' if success else '❌ FAILED'}")
        
        return success
        
    except Exception as e:
        logger.error(f"Performance test failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    logger.info("🚀 Starting optimized TGE monitoring system tests")
    logger.info("=" * 60)
    
    tests = [
        ("Matching Logic", test_matching_logic),
        ("Deduplication", test_deduplication),
        ("Company Prioritization", test_company_prioritization),
        ("Token Symbol Detection", test_token_symbol_detection),
        ("Exclusion Patterns", test_exclusion_patterns),
        ("Performance", run_performance_test)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Running {test_name} test...")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} test PASSED")
            else:
                logger.error(f"❌ {test_name} test FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} test ERROR: {str(e)}")
    
    logger.info("\n" + "=" * 60)
    logger.info(f"🎯 TEST SUMMARY: {passed}/{total} tests passed ({passed/total:.0%})")
    
    if passed == total:
        logger.info("🎉 All tests passed! The optimized system is ready for deployment.")
        sys.exit(0)
    else:
        logger.error("⚠️  Some tests failed. Please review the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()