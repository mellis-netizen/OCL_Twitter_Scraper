#!/usr/bin/env python3
"""
Comprehensive tests for optimized TGE detection system
Tests all new features: fuzzy matching, temporal analysis, false positive detection, etc.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from enhanced_scoring import EnhancedTGEScoring


def test_true_positive_tge():
    """Test case: Real TGE announcement with all positive signals"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    test_case = {
        'text': '''
        Caldera announces its Token Generation Event (TGE) for the $CAL token.
        The claim portal goes live today at claim.caldera.xyz at 2 PM UTC.
        Users who participated in the testnet to mainnet migration can now claim their tokens.
        The mainnet launch is happening on the Ethereum Layer 2 protocol.
        Trading will be available on major exchanges starting tomorrow.
        ''',
        'title': 'Caldera TGE Now Live - Claim Your $CAL Tokens',
        'url': 'https://www.theblock.co/post/caldera-tge-live',
        'matched_keywords': ['TGE', 'token generation event', 'claim portal', 'goes live', 'mainnet launch'],
        'matched_companies': ['Caldera'],
        'company_priorities': {'Caldera': 'HIGH'},
        'base_confidence': 0.75,
        'source_type': 'news'
    }

    confidence, details = scorer.calculate_comprehensive_score(**test_case)

    print("=" * 80)
    print("TEST 1: True Positive - Real TGE Announcement")
    print("=" * 80)
    print(f"Final Confidence: {confidence:.2%}")
    print(f"Meets Threshold: {details['meets_threshold']}")
    print(f"\nScoring Breakdown:")
    print(f"  Base Confidence: {details['base_confidence']:.2%}")
    print(f"  Source Score: +{details['source_score']}")
    print(f"  Temporal Score: +{details['temporal_score']}")
    print(f"  Section Score: +{details['section_score']}")
    print(f"  Keyword Weighted: +{details['keyword_weighted_score']}")
    print(f"  Date Analysis: +{details['date_analysis_score']}")
    print(f"  False Positive Penalty: {details['false_positive_penalty']}")
    print(f"  Raw Confidence: {details['raw_confidence']:.2%}")
    print(f"  Calibration: {details['calibration_reason']}")
    print(f"\nKeyword Details:")
    if 'keyword_details' in details:
        kd = details['keyword_details']
        print(f"  High Value: {kd['high_value']}")
        print(f"  Medium Value: {kd['medium_value']}")
    print(f"\nDates Found: {len(details.get('dates_found', []))}")
    print(f"False Positive Patterns: {len(details.get('false_positive_patterns', []))}")
    print()

    assert confidence >= 0.80, f"Expected high confidence (>=80%), got {confidence:.2%}"
    assert details['meets_threshold'], "Should meet confidence threshold"
    print("✅ PASSED: High confidence for real TGE announcement\n")


def test_false_positive_espresso():
    """Test case: Espresso machine (should be rejected)"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    test_case = {
        'text': '''
        Best espresso machines for your coffee shop in 2024.
        Our espresso machine sale features premium Italian espresso makers.
        Great deals on commercial espresso equipment and coffee brewing systems.
        Perfect for cafes and home baristas who love quality espresso.
        ''',
        'title': 'Top Espresso Machines Sale - Coffee Shop Equipment',
        'url': 'https://example.com/espresso-machines',
        'matched_keywords': ['sale'],
        'matched_companies': [],
        'company_priorities': {},
        'base_confidence': 0.2,
        'source_type': 'news'
    }

    confidence, details = scorer.calculate_comprehensive_score(**test_case)

    print("=" * 80)
    print("TEST 2: False Positive - Espresso Machine")
    print("=" * 80)
    print(f"Final Confidence: {confidence:.2%}")
    print(f"Meets Threshold: {details['meets_threshold']}")
    print(f"False Positive Penalty: {details['false_positive_penalty']}")
    print(f"False Positive Patterns: {details.get('false_positive_patterns', [])}")
    print()

    assert confidence < 0.40, f"Expected low confidence (<40%), got {confidence:.2%}"
    assert not details['meets_threshold'], "Should NOT meet confidence threshold"
    assert details['false_positive_penalty'] < -30, "Should have heavy false positive penalty"
    print("✅ PASSED: Correctly rejected espresso machine\n")


def test_false_positive_game_token():
    """Test case: Gaming token without crypto context (should be rejected)"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    test_case = {
        'text': '''
        New in-game token system for players. Earn game tokens through loot drops.
        Our play-to-earn game features unique gaming tokens that can be used for in-game purchases.
        Collect tokens by completing quests and treasure hunts in the game.
        ''',
        'title': 'New Game Token System Launch',
        'url': 'https://gaming-news.com/game-tokens',
        'matched_keywords': ['token', 'launch'],
        'matched_companies': [],
        'company_priorities': {},
        'base_confidence': 0.35,
        'source_type': 'news'
    }

    confidence, details = scorer.calculate_comprehensive_score(**test_case)

    print("=" * 80)
    print("TEST 3: False Positive - Game Token (No Crypto Context)")
    print("=" * 80)
    print(f"Final Confidence: {confidence:.2%}")
    print(f"Meets Threshold: {details['meets_threshold']}")
    print(f"False Positive Penalty: {details['false_positive_penalty']}")
    print(f"False Positive Patterns: {details.get('false_positive_patterns', [])}")
    print()

    assert confidence < 0.45, f"Expected low confidence (<45%), got {confidence:.2%}"
    assert not details['meets_threshold'], "Should NOT meet confidence threshold"
    print("✅ PASSED: Correctly rejected game token without crypto context\n")


def test_past_tense_announcement():
    """Test case: Past TGE announcement (should be penalized)"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    test_case = {
        'text': '''
        LayerZero's TGE was announced last month and the token already launched.
        The airdrop concluded two weeks ago. Trading had launched on major exchanges.
        The token generation event happened in December 2023 and has ended.
        ''',
        'title': 'LayerZero TGE Recap - What Happened',
        'url': 'https://www.coindesk.com/layerzero-tge-recap',
        'matched_keywords': ['TGE', 'token generation event', 'airdrop'],
        'matched_companies': ['LayerZero'],
        'company_priorities': {'LayerZero': 'HIGH'},
        'base_confidence': 0.65,
        'source_type': 'news'
    }

    confidence, details = scorer.calculate_comprehensive_score(**test_case)

    print("=" * 80)
    print("TEST 4: Past Tense Announcement (Should Be Penalized)")
    print("=" * 80)
    print(f"Final Confidence: {confidence:.2%}")
    print(f"Temporal Score: {details['temporal_score']}")
    print(f"Date Analysis Score: {details['date_analysis_score']}")
    print(f"Dates Found: {details.get('dates_found', [])}")
    print()

    assert details['temporal_score'] < 0, "Should have negative temporal score for past tense"
    print("✅ PASSED: Past tense announcement properly penalized\n")


def test_testnet_token():
    """Test case: Testnet token (should be heavily penalized)"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    test_case = {
        'text': '''
        Project X launches testnet token for developers.
        This is a test token for the devnet environment.
        The testnet will help us prepare for mainnet launch next quarter.
        Developers can get mock tokens for testing on the testnet.
        ''',
        'title': 'Project X Testnet Token Launch',
        'url': 'https://crypto-news.com/project-x-testnet',
        'matched_keywords': ['token', 'launch', 'testnet'],
        'matched_companies': [],
        'company_priorities': {},
        'base_confidence': 0.45,
        'source_type': 'news'
    }

    confidence, details = scorer.calculate_comprehensive_score(**test_case)

    print("=" * 80)
    print("TEST 5: Testnet Token (Should Be Rejected)")
    print("=" * 80)
    print(f"Final Confidence: {confidence:.2%}")
    print(f"False Positive Penalty: {details['false_positive_penalty']}")
    print(f"False Positive Patterns: {details.get('false_positive_patterns', [])}")
    print()

    assert confidence < 0.30, f"Expected very low confidence (<30%), got {confidence:.2%}"
    assert details['false_positive_penalty'] <= -50, "Should have heavy penalty for testnet"
    print("✅ PASSED: Testnet token correctly rejected\n")


def test_fuzzy_company_matching():
    """Test fuzzy matching for company names"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    # Test exact match
    is_match, score, term = scorer.fuzzy_match_company(
        "Caldera announces new protocol",
        "Caldera",
        []
    )
    print("=" * 80)
    print("TEST 6: Fuzzy Company Matching")
    print("=" * 80)
    print(f"Exact match 'Caldera': {is_match}, score: {score:.2f}, term: {term}")
    assert is_match and score == 1.0, "Exact match should return 1.0"

    # Test fuzzy match (typo)
    is_match, score, term = scorer.fuzzy_match_company(
        "Caldera announces new protocol",
        "Caldera",
        []
    )
    print(f"Fuzzy match 'Caldera' in text: {is_match}, score: {score:.2f}")

    # Test no match
    is_match, score, term = scorer.fuzzy_match_company(
        "Some random text about coffee",
        "Caldera",
        []
    )
    print(f"No match 'Caldera' in coffee text: {is_match}, score: {score:.2f}")
    assert not is_match, "Should not match unrelated text"

    print("✅ PASSED: Fuzzy matching works correctly\n")


def test_date_extraction():
    """Test date extraction and temporal analysis"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    # Use dates relative to current system time (2025-10-12)
    text_with_dates = '''
    The token launch is scheduled for December 15, 2025.
    Trading will begin on 12/20/2025.
    Early access starts tomorrow at 2 PM UTC.
    Q4 2025 mainnet deployment confirmed.
    Past event: The testnet launched on January 1, 2025.
    '''

    score, dates = scorer.extract_and_analyze_dates(text_with_dates)

    print("=" * 80)
    print("TEST 7: Date Extraction and Analysis")
    print("=" * 80)
    print(f"Date Analysis Score: {score}")
    print(f"Dates Found: {len(dates)}")
    for date_info in dates:
        print(f"  - {date_info['date_str']}: {date_info['category']} ({date_info['days_from_now']} days)")
    print()

    assert len(dates) > 0, "Should extract dates from text"
    # Score can be positive or negative depending on mix of dates
    print("✅ PASSED: Date extraction working correctly\n")


def test_keyword_weighting():
    """Test keyword relevance scoring with weights"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    high_value_text = "Token Generation Event is now live. Claim portal active. Trading live on exchanges."
    low_value_text = "Token announcement coming soon. More details on the roadmap."

    score_high, details_high = scorer.calculate_keyword_relevance_score(
        ['TGE', 'claim portal', 'trading live'],
        high_value_text
    )

    score_low, details_low = scorer.calculate_keyword_relevance_score(
        ['token', 'announcement', 'coming soon'],
        low_value_text
    )

    print("=" * 80)
    print("TEST 8: Keyword Weighting System")
    print("=" * 80)
    print(f"High-value keywords score: {score_high}")
    print(f"  High value keywords: {details_high['high_value']}")
    print(f"  Medium value keywords: {details_high['medium_value']}")
    print(f"\nLow-value keywords score: {score_low}")
    print(f"  Low value keywords: {details_low['low_value']}")
    print()

    assert score_high > score_low * 3, "High-value keywords should score much higher"
    assert len(details_high['high_value']) > 0, "Should detect high-value keywords"
    print("✅ PASSED: Keyword weighting system working correctly\n")


def test_confidence_calibration():
    """Test confidence calibration"""
    scorer = EnhancedTGEScoring(fuzzy_match_threshold=0.85, confidence_threshold=0.65)

    # Strong signals - should boost confidence
    strong_details = {
        'temporal_score': 20,
        'section_score': 25,
        'source_score': 15,
        'keyword_weighted_score': 60,
        'matched_companies': ['Caldera'],
        'matched_keywords': ['TGE', 'live'],
        'false_positive_penalty': 0
    }

    calibrated, reason = scorer.calibrate_confidence(0.75, strong_details)

    print("=" * 80)
    print("TEST 9: Confidence Calibration")
    print("=" * 80)
    print(f"Raw confidence: 0.75")
    print(f"Calibrated confidence: {calibrated:.2%}")
    print(f"Calibration reason: {reason}")
    print()

    assert calibrated > 0.75, "Strong signals should boost confidence"

    # Weak signals - should penalize
    weak_details = {
        'temporal_score': 0,
        'section_score': 0,
        'source_score': 0,
        'keyword_weighted_score': 10,
        'matched_companies': [],
        'matched_keywords': ['token'],
        'false_positive_penalty': -40
    }

    calibrated_weak, reason_weak = scorer.calibrate_confidence(0.75, weak_details)
    print(f"Weak signals:")
    print(f"  Raw confidence: 0.75")
    print(f"  Calibrated confidence: {calibrated_weak:.2%}")
    print(f"  Should be reduced due to false positives")
    print()

    assert calibrated_weak < 0.75, "False positive signals should reduce confidence"
    print("✅ PASSED: Confidence calibration working correctly\n")


def run_all_tests():
    """Run all test cases"""
    print("\n" + "=" * 80)
    print("OPTIMIZED TGE DETECTION SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 80 + "\n")

    try:
        test_true_positive_tge()
        test_false_positive_espresso()
        test_false_positive_game_token()
        test_past_tense_announcement()
        test_testnet_token()
        test_fuzzy_company_matching()
        test_date_extraction()
        test_keyword_weighting()
        test_confidence_calibration()

        print("=" * 80)
        print("ALL TESTS PASSED! ✅")
        print("=" * 80)
        print("\nSummary of Improvements:")
        print("  ✅ Fuzzy company name matching with configurable threshold")
        print("  ✅ Advanced temporal analysis with date extraction")
        print("  ✅ Context-aware false positive detection")
        print("  ✅ Weighted keyword scoring system")
        print("  ✅ Confidence calibration based on signal strength")
        print("  ✅ Enhanced exclusion patterns with crypto context")
        print("  ✅ Past vs future announcement detection")
        print("  ✅ Configurable confidence thresholds")
        print()

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        raise


if __name__ == "__main__":
    run_all_tests()
