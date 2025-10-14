#!/usr/bin/env python3
"""
Keyword Precision Specialist Agent
Optimizes TGE keyword matching and reduces false positives
"""

import asyncio
import re
from typing import Dict, List, Any, Tuple
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from .base_agent import TGEAgent, AgentCapability, TaskResult


class KeywordPrecisionSpecialist(TGEAgent):
    """
    Specialized agent for keyword matching precision
    Focuses on:
    - Keyword matching precision
    - False positive elimination
    - Company name matching accuracy
    - Context-aware filtering
    """

    def __init__(self, agent_id: str, config: Dict[str, Any] = None):
        super().__init__(
            agent_id=agent_id,
            agent_type="keyword-precision-specialist",
            capabilities=[
                AgentCapability.NLP_ANALYSIS,
                AgentCapability.PERFORMANCE_TUNING
            ],
            specializations=[
                "tge-keyword-matching",
                "false-positive-elimination",
                "company-name-disambiguation",
                "context-aware-filtering"
            ],
            config=config
        )

        # Precision-specific configuration
        self.target_precision = 0.95  # 95% precision goal
        self.target_false_positive_reduction = 0.50  # 50% reduction goal

    async def execute_specialized_task(
        self,
        task: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Execute keyword precision optimization task"""

        task_type = task.get('type', 'analyze')
        target_files = task.get('target_files', [])

        findings = []
        optimizations = []

        try:
            if task_type == 'analyze':
                # Analyze keyword matching logic
                for file_path in target_files:
                    file_findings, file_optimizations = await self._analyze_keyword_logic(file_path)
                    findings.extend(file_findings)
                    optimizations.extend(file_optimizations)

            elif task_type == 'optimize_keywords':
                # Optimize keyword lists
                keyword_optimizations = await self._optimize_keyword_lists()
                optimizations.extend(keyword_optimizations)

            elif task_type == 'reduce_false_positives':
                # Generate false positive reduction strategies
                fp_optimizations = await self._reduce_false_positives()
                optimizations.extend(fp_optimizations)

            elif task_type == 'company_disambiguation':
                # Improve company name matching
                company_optimizations = await self._improve_company_matching()
                optimizations.extend(company_optimizations)

        except Exception as e:
            self.logger.error(f"Error executing keyword specialist task: {e}")
            findings.append({
                'type': 'error',
                'severity': 'high',
                'message': str(e)
            })

        return findings, optimizations

    async def _analyze_keyword_logic(
        self,
        file_path: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Analyze keyword matching logic for optimization opportunities"""

        findings = []
        optimizations = []

        try:
            full_path = Path(file_path)
            if not full_path.exists():
                full_path = Path('../') / file_path

            if not full_path.exists():
                return findings, optimizations

            with open(full_path, 'r') as f:
                content = f.read()

            # Pattern 1: Simple string matching without context
            if 'keyword in text' in content or 'keyword.lower() in text.lower()' in content:
                optimizations.append({
                    'type': 'context_scoring',
                    'file': str(file_path),
                    'severity': 'high',
                    'current_issue': 'Simple substring matching without context',
                    'recommendation': 'Implement context-aware scoring with surrounding words',
                    'implementation': {
                        'method': 'Context window analysis',
                        'window_size': '50 characters before/after match',
                        'scoring_factors': [
                            'Proximity to company name',
                            'Presence of action verbs (announce, launch, release)',
                            'Date/time indicators',
                            'Confidence signals (official, confirmed)'
                        ]
                    },
                    'potential_improvement': '40-60% false positive reduction',
                    'priority': 'critical'
                })

            # Pattern 2: No company name validation
            if 'TGE' in content and 'company' in content.lower():
                optimizations.append({
                    'type': 'company_validation',
                    'file': str(file_path),
                    'severity': 'critical',
                    'current_issue': 'TGE keywords detected without company context validation',
                    'recommendation': 'Require company name proximity for high confidence matches',
                    'implementation': {
                        'rule': 'Company name must appear within 200 characters of TGE keyword',
                        'fuzzy_matching': 'Use Levenshtein distance for name variations',
                        'alias_support': 'Check company aliases and common misspellings'
                    },
                    'potential_improvement': '50-70% precision improvement',
                    'priority': 'critical'
                })

            # Pattern 3: Missing exclusion pattern filtering
            if 'keyword' in content and 'exclusion' not in content.lower():
                optimizations.append({
                    'type': 'exclusion_filtering',
                    'file': str(file_path),
                    'severity': 'high',
                    'current_issue': 'No exclusion patterns detected',
                    'recommendation': 'Implement multi-stage exclusion filtering',
                    'implementation': {
                        'stage_1': 'Pre-filter with known false positive patterns',
                        'stage_2': 'Context-based exclusions (historical, tutorial, opinion)',
                        'stage_3': 'Company-specific exclusions (fabric softener, coffee shop)'
                    },
                    'potential_improvement': '30-40% false positive reduction',
                    'priority': 'high'
                })

            # Pattern 4: No confidence scoring
            if 'match' in content and 'confidence' not in content.lower() and 'score' not in content.lower():
                optimizations.append({
                    'type': 'confidence_scoring',
                    'file': str(file_path),
                    'severity': 'high',
                    'current_issue': 'Binary matching without confidence scores',
                    'recommendation': 'Implement multi-factor confidence scoring',
                    'implementation': {
                        'factors': {
                            'keyword_tier': 'High/medium/low confidence keywords',
                            'company_presence': 'Company name found nearby',
                            'source_credibility': 'Source reliability score',
                            'action_indicators': 'Action verbs present',
                            'temporal_indicators': 'Date/time mentions',
                            'context_relevance': 'Surrounding text analysis'
                        },
                        'threshold': 'Configurable confidence threshold (0.75 recommended)'
                    },
                    'potential_improvement': '60-80% precision improvement',
                    'priority': 'critical'
                })

            # Pattern 5: Regex patterns not optimized
            regex_patterns = re.findall(r're\.(search|findall|match)\(["\'](.+?)["\']\)', content)
            if len(regex_patterns) > 5:
                optimizations.append({
                    'type': 'regex_optimization',
                    'file': str(file_path),
                    'severity': 'medium',
                    'current_issue': f'Found {len(regex_patterns)} regex patterns',
                    'recommendation': 'Pre-compile regex patterns and optimize for performance',
                    'implementation': {
                        'method': 'Compile patterns at module level',
                        'optimization': 'Use non-capturing groups (?:) where possible',
                        'caching': 'Cache compiled patterns'
                    },
                    'potential_improvement': '20-30% matching speed increase',
                    'priority': 'medium'
                })

        except Exception as e:
            self.logger.error(f"Error analyzing keyword logic in {file_path}: {e}")

        return findings, optimizations

    async def _optimize_keyword_lists(self) -> List[Dict[str, Any]]:
        """Generate keyword list optimization recommendations"""

        optimizations = []

        # Tiered keyword system
        optimizations.append({
            'type': 'keyword_tiering',
            'recommendation': 'Implement tiered keyword confidence system',
            'implementation': {
                'tier_1_high_confidence': {
                    'keywords': [
                        'TGE', 'token generation event', 'token launch',
                        'airdrop is live', 'claim your tokens', 'token distribution live'
                    ],
                    'base_confidence': 0.9,
                    'requires_company': False
                },
                'tier_2_medium_confidence': {
                    'keywords': [
                        'mainnet launch', 'token listing', 'governance token',
                        'airdrop', 'token sale', 'IDO'
                    ],
                    'base_confidence': 0.6,
                    'requires_company': True
                },
                'tier_3_low_confidence': {
                    'keywords': [
                        'announcing', 'coming soon', 'launching on',
                        'available on', 'tokenomics'
                    ],
                    'base_confidence': 0.3,
                    'requires_company': True,
                    'requires_additional_signals': True
                }
            },
            'potential_improvement': '50-70% precision increase',
            'priority': 'critical'
        })

        # Action-oriented keyword weighting
        optimizations.append({
            'type': 'action_weighting',
            'recommendation': 'Weight keywords by action strength',
            'implementation': {
                'strong_actions': {
                    'keywords': ['is live', 'now available', 'claim now', 'launched', 'deployed'],
                    'multiplier': 1.5
                },
                'medium_actions': {
                    'keywords': ['announcing', 'introducing', 'revealed', 'confirmed'],
                    'multiplier': 1.2
                },
                'weak_actions': {
                    'keywords': ['planning', 'considering', 'may launch', 'rumors'],
                    'multiplier': 0.5
                }
            },
            'potential_improvement': '30-40% accuracy improvement',
            'priority': 'high'
        })

        # Temporal relevance
        optimizations.append({
            'type': 'temporal_filtering',
            'recommendation': 'Filter based on temporal relevance',
            'implementation': {
                'exclude_patterns': [
                    'last year', 'in 2023', 'historical', 'anniversary',
                    'recap of', 'looking back', 'previous'
                ],
                'boost_patterns': [
                    'today', 'now', 'this week', 'just announced',
                    'breaking', 'live now', 'currently'
                ],
                'recency_window': '7 days for maximum relevance'
            },
            'potential_improvement': '40-50% false positive reduction',
            'priority': 'high'
        })

        return optimizations

    async def _reduce_false_positives(self) -> List[Dict[str, Any]]:
        """Generate false positive reduction strategies"""

        optimizations = []

        # Context-aware filtering
        optimizations.append({
            'type': 'context_filtering',
            'recommendation': 'Implement advanced context-aware filtering',
            'implementation': {
                'content_type_detection': {
                    'tutorial': ['how to', 'guide', 'explained', 'walkthrough'],
                    'opinion': ['my take', 'i think', 'prediction', 'forecast'],
                    'historical': ['recap', 'looking back', 'history of', 'in 2023'],
                    'speculative': ['rumor', 'allegedly', 'unconfirmed', 'could be']
                },
                'action': 'Exclude or heavily penalize these content types',
                'confidence_reduction': '-0.5 for each detected pattern'
            },
            'potential_improvement': '60-70% false positive reduction',
            'priority': 'critical'
        })

        # Negative signal detection
        optimizations.append({
            'type': 'negative_signals',
            'recommendation': 'Detect and weight negative signals',
            'implementation': {
                'negation_detection': {
                    'patterns': ['not launching', 'no token', 'postponed', 'cancelled', 'delayed'],
                    'action': 'Exclude matches with negations near keywords'
                },
                'uncertainty_markers': {
                    'patterns': ['may', 'might', 'could', 'possibly', 'rumored to'],
                    'action': 'Reduce confidence by 50%'
                },
                'question_forms': {
                    'patterns': ['will.*launch', 'when.*token', 'is.*planning'],
                    'action': 'Mark as low confidence (0.2)'
                }
            },
            'potential_improvement': '40-50% precision improvement',
            'priority': 'high'
        })

        # Source credibility weighting
        optimizations.append({
            'type': 'source_credibility',
            'recommendation': 'Weight matches by source credibility',
            'implementation': {
                'tier_1_sources': {
                    'sources': ['@TheBlock__', '@CoinDesk', '@DecryptMedia', 'Official company account'],
                    'confidence_multiplier': 1.3
                },
                'tier_2_sources': {
                    'sources': ['@Cointelegraph', '@Messari', 'Major news RSS'],
                    'confidence_multiplier': 1.1
                },
                'tier_3_sources': {
                    'sources': ['Individual influencers', 'Minor news sites'],
                    'confidence_multiplier': 0.9
                },
                'unverified_sources': {
                    'confidence_multiplier': 0.6
                }
            },
            'potential_improvement': '30-40% accuracy improvement',
            'priority': 'high'
        })

        return optimizations

    async def _improve_company_matching(self) -> List[Dict[str, Any]]:
        """Generate company name matching improvements"""

        optimizations = []

        # Fuzzy matching implementation
        optimizations.append({
            'type': 'fuzzy_matching',
            'recommendation': 'Implement fuzzy matching for company names',
            'implementation': {
                'method': 'Levenshtein distance',
                'threshold': 'Distance <= 2 for short names, <= 3 for long names',
                'use_cases': [
                    'Handle typos (Curvance vs Curvence)',
                    'Variations (TreasureDAO vs Treasure DAO)',
                    'Missing punctuation (Huddle01 vs Huddle 01)'
                ],
                'library': 'python-Levenshtein or fuzzywuzzy'
            },
            'potential_improvement': '20-30% company detection improvement',
            'priority': 'high'
        })

        # Alias expansion
        optimizations.append({
            'type': 'alias_expansion',
            'recommendation': 'Expand company alias system',
            'implementation': {
                'structure': {
                    'primary_name': 'Curvance',
                    'aliases': ['Curvance Finance', 'Curvance Protocol', '@CurvanceFinance'],
                    'common_misspellings': ['Curvence', 'Curvanse'],
                    'exclusions': ['curvature', 'curve finance']
                },
                'matching_priority': 'Primary name > Aliases > Fuzzy match',
                'confidence_adjustment': 'Full confidence for exact match, -0.1 for fuzzy'
            },
            'potential_improvement': '40-50% company attribution accuracy',
            'priority': 'critical'
        })

        # Context proximity scoring
        optimizations.append({
            'type': 'proximity_scoring',
            'recommendation': 'Score company-keyword proximity',
            'implementation': {
                'distance_bands': {
                    'adjacent': {
                        'range': '0-50 characters',
                        'confidence_multiplier': 1.3
                    },
                    'near': {
                        'range': '51-150 characters',
                        'confidence_multiplier': 1.1
                    },
                    'same_paragraph': {
                        'range': '151-300 characters',
                        'confidence_multiplier': 1.0
                    },
                    'distant': {
                        'range': '>300 characters',
                        'confidence_multiplier': 0.7
                    }
                },
                'method': 'Calculate character distance between company and TGE keyword'
            },
            'potential_improvement': '30-40% precision improvement',
            'priority': 'high'
        })

        return optimizations
