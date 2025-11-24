#!/usr/bin/env python3
"""
GitHub Trending Tracker - Python RAVL Loop with API Integration

Demonstrates:
- API integration without authentication
- Self-healing data ingestion
- Pattern learning (what makes repos trend)
- Execution vs domain learning separation
- Data persistence and history tracking

Learning Objectives:
1. API integration patterns in RAVL
2. Handling rate limits and API errors
3. Domain learning (trending patterns)
4. Execution learning (optimal API strategies)
5. Data quality verification

No GitHub authentication required - uses public API.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import sys
import json

# Add framework common to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'ravl' / 'common'))

from ravl_base import BaseRAVLLoop

try:
    import requests
except ImportError:
    print("Installing required dependency: requests")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests>=2.31.0"])
    import requests


class GitHubTrendingTracker(BaseRAVLLoop):
    """
    Tracks GitHub trending repositories and learns what makes repos trend

    This loop demonstrates:
    - API integration (GitHub trending search)
    - Self-healing (handles rate limits, API changes)
    - Domain learning (trending patterns, topic clusters)
    - Execution learning (API strategies, error recovery)
    - Dual verification (API success + data quality)
    """

    def __init__(self, loop_dir: Path):
        """Initialize the GitHub Trending Tracker"""
        learning_path = loop_dir / 'learnings' / 'loop_learning'
        model_path = learning_path / 'model.yml'
        super().__init__(model_path, "GitHub Trending Tracker", learning_path=learning_path)

        self.loop_dir = loop_dir
        self.output_dir = loop_dir / 'output'
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # GitHub API endpoint (no auth required for public data)
        self.api_url = "https://api.github.com/search/repositories"

    def reflect(self) -> Dict[str, Any]:
        """
        PHASE 1: REFLECT

        Load previous learnings about trending patterns and API behavior.
        """
        print("\n" + "="*80)
        print(" Step 1 of 4: [R]EFLECT")
        print("="*80)

        # Load previous model
        model = self.load_model_with_timestamp(self._default_model)

        total_runs = model.get('statistics', {}).get('total_runs', 0)
        trending_patterns = model.get('trending_patterns', {})
        api_health = model.get('api_health', {})

        print(f"\n📊 Previous Learnings:")
        print(f"   Total runs: {total_runs}")
        print(f"   Top trending topics: {list(trending_patterns.get('top_topics', {}).keys())[:5]}")
        print(f"   API success rate: {api_health.get('success_rate', 0):.1%}")

        # Calculate date range for query (last 7 days)
        week_ago = (datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    .date().isoformat())

        reflection = {
            'previous_model': model,
            'is_first_run': total_runs == 0,
            'query_date': week_ago,
            'current_timestamp': datetime.now(timezone.utc).isoformat()
        }

        if reflection['is_first_run']:
            print("\n💡 First run - establishing baseline trending patterns")
        else:
            print(f"\n💡 Run #{total_runs + 1} - tracking trending evolution")

        return reflection

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        PHASE 2: ACT

        Fetch trending repositories from GitHub and analyze them.
        """
        print("\n" + "="*80)
        print(" Step 2 of 4: [A]CT")
        print("="*80)

        query_date = reflection['query_date']

        try:
            # Query GitHub for repos created recently with many stars
            # This approximates "trending" without needing the trending page
            params = {
                'q': f'created:>{query_date} stars:>100',
                'sort': 'stars',
                'order': 'desc',
                'per_page': 30
            }

            print(f"\n🔍 Fetching trending repos from GitHub...")
            print(f"   Query: created after {query_date}, sorted by stars")

            response = requests.get(self.api_url, params=params, timeout=10)

            # Check for rate limiting
            if response.status_code == 403:
                return {
                    'error': 'rate_limit_exceeded',
                    'message': 'GitHub API rate limit exceeded',
                    'repositories': []
                }

            response.raise_for_status()
            data = response.json()

            repos = self._extract_repo_data(data.get('items', []))

            print(f"\n✅ Fetched {len(repos)} trending repositories")

            # Analyze patterns
            analysis = self._analyze_trends(repos)

            print(f"\n📊 Trending Analysis:")
            print(f"   Top languages: {list(analysis['languages'].keys())[:5]}")
            print(f"   Top topics: {list(analysis['topics'].keys())[:5]}")
            print(f"   Avg stars: {analysis['avg_stars']:.0f}")

            # Save output
            output_file = self.output_dir / f'trending_{datetime.now(timezone.utc).strftime("%Y-%m-%d")}.json'
            with open(output_file, 'w') as f:
                json.dump({
                    'repositories': repos,
                    'analysis': analysis,
                    'metadata': {
                        'fetch_timestamp': datetime.now(timezone.utc).isoformat(),
                        'query_date': query_date,
                        'total_repos': len(repos)
                    }
                }, f, indent=2)

            print(f"\n💾 Saved to: {output_file}")

            return {
                'repositories': repos,
                'analysis': analysis,
                'output_file': str(output_file),
                'api_response_code': response.status_code
            }

        except requests.exceptions.RequestException as e:
            print(f"\n❌ API Error: {e}")
            return {
                'error': 'api_error',
                'message': str(e),
                'repositories': []
            }

    def verify(self, reflection: Dict[str, Any], action_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        PHASE 3: VERIFY

        Verify API call succeeded and data quality is acceptable.
        """
        print("\n" + "="*80)
        print(" Step 3 of 4: [V]ERIFY")
        print("="*80)

        checks = {}

        # Check for errors
        if 'error' in action_result:
            checks['no_api_errors'] = False
            checks['error_type'] = action_result['error']
        else:
            checks['no_api_errors'] = True

        # Check data quality
        repos = action_result.get('repositories', [])
        checks['has_repositories'] = len(repos) > 0
        checks['min_repos_fetched'] = len(repos) >= 10
        checks['has_analysis'] = 'analysis' in action_result

        # Check repo data completeness
        if repos:
            complete_repos = sum(1 for r in repos if all(k in r for k in ['name', 'stars', 'language']))
            checks['data_completeness'] = complete_repos / len(repos) >= 0.9
        else:
            checks['data_completeness'] = False

        # Overall pass/fail
        passed = all([
            checks.get('no_api_errors', False),
            checks.get('has_repositories', False),
            checks.get('has_analysis', False),
            checks.get('data_completeness', False)
        ])

        verification = {
            'passed': passed,
            'checks': checks,
            'repositories_count': len(repos)
        }

        print(f"\n🔍 Verification Results:")
        for check, result in checks.items():
            status = '✅' if result else '❌'
            print(f"   {status} {check}")

        if passed:
            print(f"\n✅ All checks passed!")
        else:
            print(f"\n❌ Verification failed")

        return verification

    def learn(self, reflection: Dict[str, Any], action_result: Dict[str, Any],
              verification: Dict[str, Any]) -> None:
        """
        PHASE 4: LEARN

        Update model with trending patterns and API behavior learnings.
        """
        print("\n" + "="*80)
        print(" Step 4 of 4: [L]EARN")
        print("="*80)

        model = reflection['previous_model']

        # Update statistics
        stats = model.get('statistics', {})
        stats['total_runs'] = stats.get('total_runs', 0) + 1
        stats['successful_runs'] = stats.get('successful_runs', 0) + (1 if verification['passed'] else 0)
        stats['failed_runs'] = stats.get('failed_runs', 0) + (0 if verification['passed'] else 1)

        # Update API health tracking
        api_health = model.get('api_health', {})
        api_health['last_response_code'] = action_result.get('api_response_code')
        api_health['success_rate'] = stats['successful_runs'] / stats['total_runs']

        # Learn trending patterns (domain learning)
        if verification['passed']:
            analysis = action_result.get('analysis', {})
            trending_patterns = self._update_trending_patterns(
                model.get('trending_patterns', {}),
                analysis
            )
        else:
            trending_patterns = model.get('trending_patterns', {})

        # Compile updated model
        updated_model = {
            'statistics': stats,
            'api_health': api_health,
            'trending_patterns': trending_patterns,
            'last_run': action_result.get('output_file', 'unknown'),
            'last_run_timestamp': reflection['current_timestamp']
        }

        print(f"\n📈 Updated Learnings:")
        print(f"   Total runs: {stats['total_runs']}")
        print(f"   Success rate: {api_health['success_rate']:.1%}")
        if trending_patterns.get('top_topics'):
            print(f"   Learned topics: {len(trending_patterns['top_topics'])}")

        # Save model
        self._save_model_with_timestamp(updated_model)

        print(f"\n💾 Model saved to learnings/loop_learning/")

    def _extract_repo_data(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Extract relevant data from GitHub API response"""
        repos = []
        for item in items:
            repos.append({
                'name': item.get('full_name', ''),
                'description': item.get('description', ''),
                'stars': item.get('stargazers_count', 0),
                'forks': item.get('forks_count', 0),
                'language': item.get('language', 'Unknown'),
                'topics': item.get('topics', []),
                'created_at': item.get('created_at', ''),
                'url': item.get('html_url', '')
            })
        return repos

    def _analyze_trends(self, repos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trending patterns in repositories"""
        from collections import Counter

        languages = Counter()
        topics = Counter()
        total_stars = 0

        for repo in repos:
            if repo['language']:
                languages[repo['language']] += 1
            for topic in repo['topics']:
                topics[topic] += 1
            total_stars += repo['stars']

        return {
            'languages': dict(languages.most_common(10)),
            'topics': dict(topics.most_common(10)),
            'avg_stars': total_stars / len(repos) if repos else 0,
            'total_repos': len(repos)
        }

    def _update_trending_patterns(self, current_patterns: Dict, new_analysis: Dict) -> Dict:
        """Update trending patterns with exponential moving average (70% history, 30% current)"""
        from collections import Counter

        if not current_patterns:
            return {
                'top_languages': new_analysis.get('languages', {}),
                'top_topics': new_analysis.get('topics', {}),
                'avg_stars_trend': [new_analysis.get('avg_stars', 0)]
            }

        # Update with exponential moving average
        top_languages = Counter(current_patterns.get('top_languages', {}))
        top_languages = {k: int(v * 0.7) for k, v in top_languages.items()}
        for lang, count in new_analysis.get('languages', {}).items():
            top_languages[lang] = top_languages.get(lang, 0) + int(count * 0.3)

        top_topics = Counter(current_patterns.get('top_topics', {}))
        top_topics = {k: int(v * 0.7) for k, v in top_topics.items()}
        for topic, count in new_analysis.get('topics', {}).items():
            top_topics[topic] = top_topics.get(topic, 0) + int(count * 0.3)

        avg_stars_trend = current_patterns.get('avg_stars_trend', [])
        avg_stars_trend.append(new_analysis.get('avg_stars', 0))
        avg_stars_trend = avg_stars_trend[-10:]  # Keep last 10

        return {
            'top_languages': dict(Counter(top_languages).most_common(10)),
            'top_topics': dict(Counter(top_topics).most_common(10)),
            'avg_stars_trend': avg_stars_trend
        }

    def _default_model(self) -> Dict[str, Any]:
        """Return default model structure"""
        return {
            'statistics': {
                'total_runs': 0,
                'successful_runs': 0,
                'failed_runs': 0
            },
            'api_health': {
                'success_rate': 0.0,
                'last_response_code': None
            },
            'trending_patterns': {},
            'last_run': None,
            'last_run_timestamp': None
        }

    def _save_model_with_timestamp(self, model: Dict[str, Any]) -> None:
        """Save model with timestamp"""
        from utils.file_utils import save_yaml_file

        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
        timestamped_path = self.learning_path / f'model-{timestamp}.yml'

        save_yaml_file(timestamped_path, model)
        save_yaml_file(self.model_path, model)


def main():
    """Run the GitHub Trending Tracker"""
    loop_dir = Path(__file__).parent
    loop = GitHubTrendingTracker(loop_dir)

    print("\n🚀 Starting GitHub Trending Tracker")
    print("="*80)

    reflection = loop.reflect()
    action_result = loop.act(reflection)
    verification = loop.verify(reflection, action_result)
    loop.learn(reflection, action_result, verification)

    print("\n" + "="*80)
    if verification['passed']:
        print("✅ GitHub Trending Tracker completed successfully")
    else:
        print("❌ GitHub Trending Tracker completed with errors")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
