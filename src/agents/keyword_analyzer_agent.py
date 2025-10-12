"""
Keyword Analyzer Agent
Advanced TGE keyword analysis and signal detection
"""

import re
from typing import Dict, Any, List, Tuple
from datetime import datetime
from collections import Counter

from src.agents.base_agent import BaseAgent


class KeywordAnalyzerAgent(BaseAgent):
    """
    Agent specialized in analyzing content for TGE-related keywords and signals
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, "keyword_analyzer", config)

        # TGE keyword categories with confidence weights
        self.keyword_categories = {
            'high_confidence': {
                'keywords': [
                    'token generation event', 'tge is live', 'airdrop is live',
                    'claim your tokens', 'token launch date', 'tokens are now available',
                    'trading is now live', 'token distribution', 'claim window'
                ],
                'weight': 30
            },
            'medium_confidence': {
                'keywords': [
                    'mainnet launch', 'tokenomics', 'token sale', 'listing',
                    'trading live', 'airdrop announcement', 'token allocation',
                    'token unlock', 'vesting schedule'
                ],
                'weight': 15
            },
            'low_confidence': {
                'keywords': [
                    'token', 'airdrop', 'launch', 'tge', 'announcement',
                    'distribution', 'claim', 'whitelist', 'snapshot'
                ],
                'weight': 5
            }
        }

        # Exclusion patterns that reduce confidence
        self.exclusion_patterns = {
            'testnet': -20,
            'game token': -15,
            'nft collection': -15,
            'price prediction': -10,
            'technical analysis': -10,
            'rumor': -10
        }

        # Compile regex patterns
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficient matching"""
        self.compiled_keywords = {}

        for category, data in self.keyword_categories.items():
            patterns = [re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
                       for kw in data['keywords']]
            self.compiled_keywords[category] = {
                'patterns': patterns,
                'weight': data['weight']
            }

        self.compiled_exclusions = {
            pattern: (re.compile(r'\b' + re.escape(pattern) + r'\b', re.IGNORECASE), weight)
            for pattern, weight in self.exclusion_patterns.items()
        }

    async def _do_initialize(self):
        """Initialize keyword analyzer"""
        self.logger.info("Keyword analyzer initialized")

        await self.store_memory('patterns', {
            'high_confidence_count': len(self.keyword_categories['high_confidence']['keywords']),
            'medium_confidence_count': len(self.keyword_categories['medium_confidence']['keywords']),
            'low_confidence_count': len(self.keyword_categories['low_confidence']['keywords']),
            'exclusion_count': len(self.exclusion_patterns)
        }, 'initialization')

    async def _execute_task_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute keyword analysis task"""
        task_type = task.get('type', 'analyze_content')

        if task_type == 'analyze_content':
            return await self._analyze_content(task)
        elif task_type == 'batch_analyze':
            return await self._batch_analyze(task)
        elif task_type == 'extract_signals':
            return await self._extract_signals(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _analyze_content(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze single content piece for TGE relevance"""
        content = task.get('content', '')
        title = task.get('title', '')
        source = task.get('source', 'unknown')

        analysis = self._perform_analysis(content, title)

        # Store analysis result
        await self.store_memory(f'analysis_{int(datetime.now().timestamp())}', {
            'source': source,
            'analysis': analysis,
            'timestamp': datetime.now().isoformat()
        }, 'analysis_results')

        # Update metrics
        await self.update_metrics({
            'total_analyzed': self.state['metrics'].get('total_analyzed', 0) + 1,
            'last_confidence': analysis['confidence']
        })

        return analysis

    async def _batch_analyze(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze multiple content pieces"""
        items = task.get('items', [])

        results = []
        for item in items:
            content = item.get('content', '')
            title = item.get('title', '')

            analysis = self._perform_analysis(content, title)
            analysis['item_id'] = item.get('id', 'unknown')
            results.append(analysis)

        # Store batch results
        await self.store_memory(f'batch_{int(datetime.now().timestamp())}', {
            'count': len(results),
            'results': results[:100],  # Store first 100
            'timestamp': datetime.now().isoformat()
        }, 'batch_results')

        # Update metrics
        await self.update_metrics({
            'total_analyzed': self.state['metrics'].get('total_analyzed', 0) + len(results),
            'batches_processed': self.state['metrics'].get('batches_processed', 0) + 1
        })

        return {
            'results': results,
            'count': len(results),
            'relevant_count': sum(1 for r in results if r['is_relevant'])
        }

    async def _extract_signals(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Extract all TGE signals from content"""
        content = task.get('content', '')
        title = task.get('title', '')

        full_text = f"{title}\n{content}".lower()

        signals = {
            'keywords': self._extract_keywords(full_text),
            'dates': self._extract_dates(full_text),
            'tokens': self._extract_token_symbols(content),
            'companies': self._extract_companies(full_text, task.get('companies', [])),
            'urgency_indicators': self._extract_urgency(full_text)
        }

        return {
            'signals': signals,
            'signal_count': sum(len(v) if isinstance(v, list) else 1 for v in signals.values())
        }

    def _perform_analysis(self, content: str, title: str = "") -> Dict[str, Any]:
        """Core analysis logic"""
        full_text = f"{title}\n{content}".lower()

        analysis = {
            'is_relevant': False,
            'confidence': 0,
            'matched_keywords': [],
            'signals': [],
            'context_snippets': []
        }

        # Match keywords by category
        for category, data in self.compiled_keywords.items():
            for pattern in data['patterns']:
                matches = pattern.finditer(full_text)
                for match in matches:
                    keyword = match.group()
                    analysis['matched_keywords'].append({
                        'keyword': keyword,
                        'category': category,
                        'position': match.start()
                    })
                    analysis['confidence'] += data['weight']
                    analysis['signals'].append(f'{category}_keyword')

                    # Extract context snippet
                    start = max(0, match.start() - 100)
                    end = min(len(full_text), match.end() + 100)
                    snippet = full_text[start:end].strip()
                    analysis['context_snippets'].append(snippet)

        # Apply exclusion patterns
        for pattern_name, (pattern, weight) in self.compiled_exclusions.items():
            if pattern.search(full_text):
                analysis['confidence'] += weight
                analysis['signals'].append(f'exclusion_{pattern_name}')

        # Token symbol detection
        tokens = self._extract_token_symbols(content)
        if tokens:
            analysis['confidence'] += 15
            analysis['signals'].append('token_symbols')
            analysis['token_symbols'] = tokens

        # Date proximity analysis
        dates = self._extract_dates(full_text)
        if dates:
            analysis['confidence'] += 10
            analysis['signals'].append('date_mentioned')
            analysis['dates'] = dates

        # Urgency detection
        urgency = self._extract_urgency(full_text)
        if urgency:
            analysis['confidence'] += urgency['weight']
            analysis['signals'].append('urgency_detected')
            analysis['urgency'] = urgency

        # Normalize confidence to 0-100
        analysis['confidence'] = max(0, min(100, analysis['confidence']))
        analysis['is_relevant'] = analysis['confidence'] >= 50

        return analysis

    def _extract_keywords(self, text: str) -> List[Dict[str, Any]]:
        """Extract all matched keywords with positions"""
        keywords = []

        for category, data in self.compiled_keywords.items():
            for pattern in data['patterns']:
                for match in pattern.finditer(text):
                    keywords.append({
                        'keyword': match.group(),
                        'category': category,
                        'position': match.start()
                    })

        return keywords

    def _extract_dates(self, text: str) -> List[Dict[str, Any]]:
        """Extract date patterns"""
        date_patterns = [
            (r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}', 'month_day'),
            (r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', 'numeric_date'),
            (r'\b(next|this)\s+(week|month)', 'relative_date'),
            (r'\bQ[1-4]\s*202\d', 'quarter'),
            (r'\b(today|tomorrow|soon)\b', 'immediate')
        ]

        dates = []
        for pattern, date_type in date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                dates.append({
                    'value': match.group(),
                    'type': date_type,
                    'position': match.start()
                })

        return dates

    def _extract_token_symbols(self, text: str) -> List[str]:
        """Extract token symbols ($TOKEN format)"""
        pattern = re.compile(r'\$[A-Z]{2,10}\b')
        return list(set(match.group() for match in pattern.finditer(text)))

    def _extract_companies(self, text: str, companies: List[Dict]) -> List[str]:
        """Extract company mentions"""
        matched_companies = []

        for company in companies:
            terms = [company.get('name', '')] + company.get('aliases', [])
            for term in terms:
                if term.lower() in text:
                    matched_companies.append(company.get('name'))
                    break

        return list(set(matched_companies))

    def _extract_urgency(self, text: str) -> Dict[str, Any]:
        """Extract urgency indicators"""
        urgency_patterns = {
            'high': [r'\bnow\b', r'\btoday\b', r'\bimmediately\b', r'\blast chance\b'],
            'medium': [r'\bsoon\b', r'\bthis week\b', r'\bupcoming\b'],
            'low': [r'\bnext month\b', r'\blater\b', r'\beventually\b']
        }

        for level, patterns in urgency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    weight = {'high': 20, 'medium': 10, 'low': 5}[level]
                    return {
                        'level': level,
                        'weight': weight,
                        'indicator': pattern
                    }

        return {}

    async def _do_shutdown(self):
        """Clean up analyzer resources"""
        self.logger.info("Shutting down keyword analyzer")
