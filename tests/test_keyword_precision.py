#!/usr/bin/env python3
"""
Comprehensive Test Suite for TGE Keyword Precision
Tests keyword effectiveness, false positive reduction, and company disambiguation
"""

import unittest
import sys
import os
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import (
    HIGH_CONFIDENCE_TGE_KEYWORDS,
    MEDIUM_CONFIDENCE_TGE_KEYWORDS,
    LOW_CONFIDENCE_TGE_KEYWORDS,
    EXCLUSION_PATTERNS,
    COMPANIES
)


class TestHighConfidenceKeywords(unittest.TestCase):
    """Test high-confidence TGE keywords for precision."""

    def setUp(self):
        """Set up test environment."""
        self.keywords = HIGH_CONFIDENCE_TGE_KEYWORDS

    def test_core_tge_terminology(self):
        """Test core TGE terms match appropriately."""
        test_cases = [
            ("Caldera announces their TGE next month", True),
            ("Token generation event scheduled for Q2", True),
            ("The token launch will happen on March 15th", True),
            ("Token is now live on mainnet", True),
            ("Discussing TGE strategies in general", True),
        ]

        for text, should_match in test_cases:
            has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
            self.assertEqual(
                has_keyword, should_match,
                f"Failed for: '{text}' (expected match: {should_match})"
            )

    def test_airdrop_patterns(self):
        """Test airdrop-related keywords."""
        test_cases = [
            ("Airdrop is live - claim now!", True),
            ("Claim your airdrop at claim.example.com", True),
            ("Airdrop campaign launching tomorrow", True),
            ("Eligible for the upcoming airdrop", True),
            ("Random airdrop from unknown project", True),  # Will be filtered by other rules
        ]

        for text, should_match in test_cases:
            has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
            self.assertEqual(has_keyword, should_match, f"Failed for: '{text}'")

    def test_trading_launch_patterns(self):
        """Test trading and listing keywords."""
        test_cases = [
            ("Token listing on Binance tomorrow", True),
            ("Trading goes live at 12 PM UTC", True),
            ("IDO starts on March 1st", True),
            ("Initial exchange offering details announced", True),
            ("Token trading is now live", True),
        ]

        for text, should_match in test_cases:
            has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
            self.assertEqual(has_keyword, should_match, f"Failed for: '{text}'")

    def test_claim_distribution_patterns(self):
        """Test claim and distribution keywords."""
        test_cases = [
            ("Token claim portal opens today", True),
            ("Claiming is live at claim.protocol.io", True),
            ("Distribution event begins next week", True),
            ("Check if you're eligible to claim tokens", True),
            ("Token unlock schedule released", True),
        ]

        for text, should_match in test_cases:
            has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
            self.assertEqual(has_keyword, should_match, f"Failed for: '{text}'")

    def test_new_live_action_keywords(self):
        """Test newly added live action keywords."""
        new_patterns = [
            "token claim live",
            "claiming portal open",
            "claim window open",
            "distribution begins",
            "tokens available now",
            "claim your tokens now",
            "distribution event started"
            # Note: "token unlock event" is in MEDIUM_CONFIDENCE_TGE_KEYWORDS
        ]

        for pattern in new_patterns:
            # Check if in keyword list
            keyword_exists = any(pattern.lower() in kw.lower() for kw in self.keywords)
            self.assertTrue(
                keyword_exists,
                f"Missing critical keyword pattern: '{pattern}'"
            )


class TestMediumConfidenceKeywords(unittest.TestCase):
    """Test medium-confidence keywords requiring context."""

    def setUp(self):
        """Set up test environment."""
        self.keywords = MEDIUM_CONFIDENCE_TGE_KEYWORDS

    def test_mainnet_launch_patterns(self):
        """Test mainnet launch keywords."""
        test_cases = [
            ("Mainnet launch scheduled for Q2", True),
            ("Protocol deployed to mainnet", True),
            ("Network launch date announced", True),
            ("Mainnet is live with token support", True),
        ]

        for text, should_match in test_cases:
            has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
            self.assertEqual(has_keyword, should_match, f"Failed for: '{text}'")

    def test_tokenomics_patterns(self):
        """Test tokenomics keywords (require context)."""
        test_cases = [
            ("Tokenomics revealed ahead of TGE", True),
            ("Token vesting schedule announced", True),
            ("Token unlock details published", True),
            ("Governance token mechanics explained", True),
        ]

        for text, should_match in test_cases:
            has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
            self.assertEqual(has_keyword, should_match, f"Failed for: '{text}'")

    def test_exchange_listing_patterns(self):
        """Test exchange listing keywords."""
        test_cases = [
            ("DEX listing confirmed for next week", True),
            ("CEX listing on major exchanges", True),
            ("Exchange listing announcement", True),
            ("Trading pair added to Uniswap", True),
        ]

        for text, should_match in test_cases:
            has_keyword = any(kw.lower() in text.lower() for kw in self.keywords)
            self.assertEqual(has_keyword, should_match, f"Failed for: '{text}'")


class TestLowConfidenceKeywords(unittest.TestCase):
    """Test low-confidence keywords (should require multiple signals)."""

    def setUp(self):
        """Set up test environment."""
        self.keywords = LOW_CONFIDENCE_TGE_KEYWORDS

    def test_generic_announcement_terms(self):
        """Test generic announcement keywords."""
        # These alone should not trigger alerts
        generic_terms = ["announce", "big news", "milestone", "coming soon"]

        for term in generic_terms:
            self.assertIn(
                term,
                [kw.lower() for kw in self.keywords],
                f"Low-confidence keyword '{term}' should be in list"
            )

    def test_timing_indicators(self):
        """Test temporal indicators."""
        timing_terms = ["next week", "this month", "launch date"]

        for term in timing_terms:
            has_keyword = any(term.lower() in kw.lower() for kw in self.keywords)
            self.assertTrue(
                has_keyword,
                f"Timing indicator '{term}' should be in low-confidence keywords"
            )

        # Check for Q1, Q2, Q3, Q4 separately (case sensitive)
        quarter_terms = ["Q1", "Q2", "Q3", "Q4"]
        for term in quarter_terms:
            has_keyword = any(term in kw for kw in self.keywords)
            self.assertTrue(
                has_keyword,
                f"Timing indicator '{term}' should be in low-confidence keywords"
            )


class TestExclusionPatterns(unittest.TestCase):
    """Test exclusion patterns to reduce false positives."""

    def setUp(self):
        """Set up test environment."""
        self.exclusions = EXCLUSION_PATTERNS

    def test_gaming_exclusions(self):
        """Test gaming/NFT false positive filters."""
        test_cases = [
            "New in-game token for rewards",
            "NFT collection drop tomorrow",
            "Play to earn game launching",
            "Achievement tokens unlocked",
            "Gaming rewards distributed",
        ]

        for text in test_cases:
            has_exclusion = any(excl.lower() in text.lower() for excl in self.exclusions)
            self.assertTrue(
                has_exclusion,
                f"Gaming content should be excluded: '{text}'"
            )

    def test_technical_exclusions(self):
        """Test technical/development false positive filters."""
        test_cases = [
            "Deployed to testnet for testing",
            "Test token minted on devnet",
            "Mock token contract created",
            "Demo tokens available",
        ]

        for text in test_cases:
            has_exclusion = any(excl.lower() in text.lower() for excl in self.exclusions)
            self.assertTrue(
                has_exclusion,
                f"Technical content should be excluded: '{text}'"
            )

    def test_analysis_exclusions(self):
        """Test opinion/analysis false positive filters."""
        test_cases = [
            "Token analysis and price prediction",
            "Market analysis for upcoming tokens",
            "Technical analysis of token performance",
            "My prediction for the token price",
        ]

        for text in test_cases:
            has_exclusion = any(excl.lower() in text.lower() for excl in self.exclusions)
            self.assertTrue(
                has_exclusion,
                f"Analysis content should be excluded: '{text}'"
            )

    def test_new_exclusion_patterns(self):
        """Test newly added exclusion patterns."""
        new_exclusions = [
            # Gaming/NFT
            ("loot drop", "New loot drop in game"),
            ("battle pass", "Season battle pass rewards"),
            ("cosmetic drop", "Exclusive cosmetic drop"),

            # Opinion/Analysis
            ("my take on", "My take on the token launch"),
            ("speculation", "Speculation about future tokens"),
            ("rumor", "Rumor suggests token soon"),

            # Historical
            ("recap of", "Recap of last year's TGE"),
            ("looking back", "Looking back at token launches"),
            ("flashback", "Flashback to 2023 TGE"),

            # Tutorial/Educational
            ("how to claim", "Tutorial: how to claim tokens"),
            ("guide to", "Guide to understanding tokenomics"),
            ("explained", "Token generation explained"),
        ]

        for pattern, example_text in new_exclusions:
            has_exclusion = any(pattern.lower() in excl.lower() for excl in self.exclusions)
            self.assertTrue(
                has_exclusion,
                f"Missing exclusion pattern: '{pattern}' (example: '{example_text}')"
            )


class TestCompanyDisambiguation(unittest.TestCase):
    """Test company name disambiguation and context detection."""

    def test_fabric_disambiguation(self):
        """Test Fabric company vs. textile fabric."""
        # Should match (crypto-related)
        crypto_cases = [
            "Fabric Protocol announces mainnet launch",
            "Fabric Cryptography token generation event",
            "Fabric Labs reveals tokenomics",
        ]

        # Should NOT match (non-crypto)
        non_crypto_cases = [
            "Buy fabric softener at the store",
            "Best cotton fabric for quilting",
            "Fabric store opens downtown",
        ]

        # Find Fabric company
        fabric_company = next((c for c in COMPANIES if c['name'] == 'Fabric'), None)
        self.assertIsNotNone(fabric_company, "Fabric company should be in config")

        # Check exclusions exist
        self.assertIn('fabric softener', fabric_company['exclusions'])
        self.assertIn('textile fabric', fabric_company['exclusions'])

    def test_caldera_disambiguation(self):
        """Test Caldera company vs. volcanic caldera."""
        # Should match (crypto-related)
        crypto_cases = [
            "Caldera announces rollup token",
            "Caldera Labs token generation",
            "Caldera Chain mainnet launch",
        ]

        # Should NOT match (non-crypto)
        non_crypto_cases = [
            "Yellowstone caldera volcanic activity",
            "Scientists study volcanic caldera formation",
            "Crater caldera discovered",
        ]

        # Find Caldera company
        caldera_company = next((c for c in COMPANIES if c['name'] == 'Caldera'), None)
        self.assertIsNotNone(caldera_company, "Caldera company should be in config")

        # Check exclusions exist
        self.assertIn('volcanic caldera', caldera_company['exclusions'])
        self.assertIn('yellowstone caldera', caldera_company['exclusions'])

    def test_espresso_disambiguation(self):
        """Test Espresso company vs. coffee."""
        # Should match (crypto-related)
        crypto_cases = [
            "Espresso Systems announces token",
            "Espresso Labs mainnet launch",
            "Espresso Protocol token generation",
        ]

        # Should NOT match (non-crypto)
        non_crypto_cases = [
            "Best espresso machine for home",
            "Coffee shop serves great espresso",
            "Starbucks espresso drinks menu",
        ]

        # Find Espresso company
        espresso_company = next((c for c in COMPANIES if c['name'] == 'Espresso'), None)
        self.assertIsNotNone(espresso_company, "Espresso company should be in config")

        # Check exclusions exist
        self.assertIn('coffee', espresso_company['exclusions'])
        self.assertIn('espresso machine', espresso_company['exclusions'])

    def test_treasure_disambiguation(self):
        """Test TreasureDAO vs. generic treasure."""
        # Find TreasureDAO company
        treasure_company = next((c for c in COMPANIES if c['name'] == 'TreasureDAO'), None)
        self.assertIsNotNone(treasure_company, "TreasureDAO company should be in config")

        # Check exclusions exist
        self.assertIn('treasure hunt', treasure_company['exclusions'])
        self.assertIn('national treasure', treasure_company['exclusions'])


class TestFalsePositiveReduction(unittest.TestCase):
    """Integration tests for overall false positive reduction."""

    def test_common_false_positives(self):
        """Test that common false positives are filtered."""
        false_positives = [
            # Gaming
            ("New NFT game announces in-game token drop", ["in-game token", "nft drop"]),
            ("Play to earn rewards in upcoming battle pass", ["play to earn", "battle pass"]),

            # Coffee/Everyday items
            ("Best espresso machines on sale this week", ["on sale", "espresso machine"]),
            ("Fabric softener deals at Target", ["fabric softener"]),

            # Generic news
            ("Bitcoin price prediction for next week", ["price prediction", "bitcoin"]),
            ("Ethereum technical analysis", ["technical analysis", "ethereum"]),

            # Historical content
            ("Looking back at major token launches of 2023", ["looking back", "in 2023"]),
            ("Recap of the best airdrops last year", ["recap of", "last year"]),

            # Tutorials
            ("How to claim airdrops - complete guide", ["how to claim", "guide to"]),
            ("Token economics explained for beginners", ["explained", "beginner's guide"]),

            # Opinion pieces
            ("My take on upcoming token launches", ["my take on"]),
            ("Speculation about potential Q2 TGEs", ["speculation"]),
        ]

        # These should all have exclusion matches
        for text, expected_patterns in false_positives:
            has_exclusion = any(excl.lower() in text.lower() for excl in EXCLUSION_PATTERNS)
            self.assertTrue(
                has_exclusion,
                f"False positive not excluded: '{text}' (expected one of {expected_patterns})"
            )

    def test_true_positives_preserved(self):
        """Ensure true positives are not filtered by exclusions."""
        true_positives = [
            "Caldera announces TGE and token distribution next month",
            "Fhenix airdrop snapshot completed - check eligibility",
            "Curvance token claim portal is now live",
            "Succinct mainnet launch with SP1 token",
            "Fabric Protocol token generation event scheduled",
        ]

        # These should NOT have exclusion matches
        for text in true_positives:
            has_exclusion = any(excl.lower() in text.lower() for excl in EXCLUSION_PATTERNS)
            self.assertFalse(
                has_exclusion,
                f"True positive incorrectly excluded: '{text}'"
            )


class TestIntegrationScenarios(unittest.TestCase):
    """Integration tests simulating real-world content analysis."""

    def test_high_confidence_scenarios(self):
        """Test scenarios that should be high confidence matches."""
        scenarios = [
            {
                'text': 'BREAKING: Caldera announces TGE for $CAL token on March 15th. Token claim portal goes live at 12 PM UTC. More details: caldera.xyz/tge',
                'expected_companies': ['Caldera'],
                'expected_keywords': ['TGE', 'token', 'claim portal'],
                'should_match': True,
                'confidence': 'HIGH'
            },
            {
                'text': 'Fhenix Protocol: Airdrop snapshot taken at block 19000000. Eligible users can claim their $FHE tokens starting tomorrow. Check eligibility at claim.fhenix.io',
                'expected_companies': ['Fhenix'],
                'expected_keywords': ['airdrop', 'snapshot', 'claim'],
                'should_match': True,
                'confidence': 'HIGH'
            },
            {
                'text': 'Curvance Finance announces token generation event. The $CURV token will be available for trading on major DEXes from March 20th. Trading goes live at 15:00 UTC.',
                'expected_companies': ['Curvance'],
                'expected_keywords': ['token generation event', 'trading', 'DEX'],
                'should_match': True,
                'confidence': 'HIGH'
            }
        ]

        for scenario in scenarios:
            text = scenario['text']

            # Check for company matches
            for company_name in scenario['expected_companies']:
                company = next((c for c in COMPANIES if c['name'] == company_name), None)
                self.assertIsNotNone(company, f"Company {company_name} not found")

            # Check for keyword matches
            has_high_conf_keyword = any(
                kw.lower() in text.lower()
                for kw in HIGH_CONFIDENCE_TGE_KEYWORDS
            )
            self.assertTrue(
                has_high_conf_keyword,
                f"No high-confidence keyword in: '{text}'"
            )

    def test_false_positive_scenarios(self):
        """Test scenarios that should be filtered as false positives."""
        scenarios = [
            {
                'text': 'Just bought a new espresso machine for my coffee shop. The steam wand is amazing!',
                'reason': 'Coffee/everyday items',
                'expected_patterns': ['espresso machine', 'coffee shop', 'buy now'],
                'should_match': False
            },
            {
                'text': 'Looking for the best fabric softener that actually works. Any recommendations?',
                'reason': 'Fabric/everyday items',
                'expected_patterns': ['fabric softener'],
                'should_match': False
            },
            {
                'text': 'Scientists discover new volcanic caldera in Yellowstone National Park. Geological activity increasing.',
                'reason': 'Volcanic caldera (not crypto)',
                'expected_patterns': ['volcanic caldera', 'yellowstone'],
                'should_match': False
            },
            {
                'text': 'New play-to-earn game launching tomorrow with in-game token rewards and NFT drops!',
                'reason': 'Gaming tokens',
                'expected_patterns': ['play to earn', 'in-game token', 'nft drop'],
                'should_match': False
            },
            {
                'text': 'My prediction for Q2 token launches: 5 projects that might announce TGE',
                'reason': 'Opinion/speculation',
                'expected_patterns': ['my take on', 'prediction for', 'speculation'],
                'should_match': False
            },
            {
                'text': 'Looking back at the biggest airdrops of 2023 - a retrospective analysis',
                'reason': 'Historical/retrospective',
                'expected_patterns': ['looking back', 'in 2023'],
                'should_match': False
            }
        ]

        for scenario in scenarios:
            text = scenario['text']
            reason = scenario['reason']
            expected = scenario['expected_patterns']

            # Check for exclusion patterns
            has_exclusion = any(
                excl.lower() in text.lower()
                for excl in EXCLUSION_PATTERNS
            )

            self.assertTrue(
                has_exclusion,
                f"False positive not excluded ({reason}): '{text}' (expected one of {expected})"
            )


class TestKeywordCoverage(unittest.TestCase):
    """Test overall keyword coverage and completeness."""

    def test_keyword_list_sizes(self):
        """Verify keyword lists meet minimum size requirements."""
        self.assertGreaterEqual(
            len(HIGH_CONFIDENCE_TGE_KEYWORDS), 70,
            "Should have at least 70 high-confidence keywords (current: 55, added: 15+)"
        )

        self.assertGreaterEqual(
            len(MEDIUM_CONFIDENCE_TGE_KEYWORDS), 30,
            "Should have at least 30 medium-confidence keywords (current: 23, added: 7+)"
        )

        self.assertGreaterEqual(
            len(EXCLUSION_PATTERNS), 40,
            "Should have at least 40 exclusion patterns (current: 16, added: 24+)"
        )

    def test_no_duplicate_keywords(self):
        """Ensure no duplicate keywords across confidence levels."""
        all_keywords = (
            HIGH_CONFIDENCE_TGE_KEYWORDS +
            MEDIUM_CONFIDENCE_TGE_KEYWORDS +
            LOW_CONFIDENCE_TGE_KEYWORDS
        )

        # Convert to lowercase for comparison
        keywords_lower = [kw.lower() for kw in all_keywords]

        # Check for duplicates
        duplicates = [kw for kw in set(keywords_lower) if keywords_lower.count(kw) > 1]

        self.assertEqual(
            len(duplicates), 0,
            f"Found duplicate keywords: {duplicates}"
        )

    def test_exclusion_pattern_validity(self):
        """Ensure exclusion patterns are valid and specific."""
        for pattern in EXCLUSION_PATTERNS:
            # Should not be empty
            self.assertTrue(len(pattern.strip()) > 0, "Empty exclusion pattern found")

            # Should not be too short (likely too generic)
            self.assertGreaterEqual(
                len(pattern.strip()), 3,
                f"Exclusion pattern too short: '{pattern}'"
            )


def run_precision_tests():
    """Run all precision tests and generate report."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestHighConfidenceKeywords))
    suite.addTests(loader.loadTestsFromTestCase(TestMediumConfidenceKeywords))
    suite.addTests(loader.loadTestsFromTestCase(TestLowConfidenceKeywords))
    suite.addTests(loader.loadTestsFromTestCase(TestExclusionPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestCompanyDisambiguation))
    suite.addTests(loader.loadTestsFromTestCase(TestFalsePositiveReduction))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationScenarios))
    suite.addTests(loader.loadTestsFromTestCase(TestKeywordCoverage))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate summary
    print("\n" + "="*70)
    print("TGE KEYWORD PRECISION TEST SUMMARY")
    print("="*70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - Keyword precision meets requirements")
    else:
        print("\n❌ TESTS FAILED - Review failures above")

    print("="*70)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_precision_tests()
    sys.exit(0 if success else 1)
