#!/usr/bin/env python3
"""
Migration Script: Reorganize existing learning files to new structure

Converts flat timestamped files into organized structure:
  - current_state/ (latest attempt)
  - recent_attempts/ (last 3 full attempts, numbered)
  - history/ (aggregated data)
"""

import json
try:
    import tomllib
except ImportError:
    import tomli as tomllib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import sys


def migrate_learning_directory(learnings_dir: Path, dry_run: bool = False) -> None:
    """
    Migrate a single learning directory to new structure

    Args:
        learnings_dir: Path to the learnings directory
        dry_run: If True, only show what would be done (don't make changes)
    """
    print(f"\nMigrating: {learnings_dir}")

    if not learnings_dir.exists():
        print("  ⚠ Directory doesn't exist, skipping")
        return

    # Find all action_result files
    action_results = sorted(learnings_dir.glob('action_result_*.json'))
    metrics_files = sorted(learnings_dir.glob('metrics_*.yml'))

    if not action_results:
        print("  ℹ No action_result files found, skipping")
        return

    print(f"  Found {len(action_results)} action_result files")
    print(f"  Found {len(metrics_files)} metrics files")

    if dry_run:
        print("  [DRY RUN] Would organize these files")
        return

    # Create new directory structure
    current_dir = learnings_dir / 'current_state'
    recent_dir = learnings_dir / 'recent_attempts'
    history_dir = learnings_dir / 'history'

    for d in [current_dir, recent_dir, history_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Process action results: keep last 3, aggregate older ones
    try:
        # Save latest to current_state/latest_attempt.json
        latest_action = _load_json(action_results[-1])
        latest_metrics = _find_matching_metrics(action_results[-1], metrics_files)

        with open(current_dir / 'latest_attempt.json', 'w', encoding='utf-8') as f:
            json.dump({'timestamp': datetime.now().isoformat(), 'action': latest_action}, f, indent=2)

        if latest_metrics:
            with open(current_dir / 'latest_metrics.yml', 'w', encoding='utf-8') as f:
                yaml.dump(latest_metrics, f)

        # Save last 3 to recent_attempts/ with numbered format
        for i, action_file in enumerate(action_results[-3:], 1):
            metrics_file = _find_matching_metrics(action_file, metrics_files)

            action_data = _load_json(action_file)
            with open(recent_dir / f'attempt_{i}_action.json', 'w', encoding='utf-8') as f:
                json.dump({'timestamp': datetime.now().isoformat(), 'action': action_data}, f, indent=2)

            if metrics_file:
                metrics_data = _load_yaml(metrics_file)
                with open(recent_dir / f'attempt_{i}_metrics.yml', 'w', encoding='utf-8') as f:
                    yaml.dump(metrics_data, f)

        # Archive older attempts into aggregated files
        if len(action_results) > 3:
            _aggregate_older_attempts(action_results[:-3], history_dir, metrics_files)

        print(f"  ✓ Organized {len(action_results)} attempts")

        # Keep learning_history.jsonl and model.yml, move others to history/
        old_files = []
        for ext in ['verification_*.json', 'inferred_dsl_*.json', 'dsl_iteration_*.json']:
            old_files.extend(learnings_dir.glob(ext))

        if old_files:
            history_archive = history_dir / 'archived_files'
            history_archive.mkdir(exist_ok=True)
            for f in old_files:
                import shutil
                shutil.move(str(f), str(history_archive / f.name))
            print(f"  ✓ Archived {len(old_files)} legacy files")

    except Exception as e:
        from pathlib import Path
        _utils_dir = Path(__file__).parent.parent / 'utils'
        import sys
        if str(_utils_dir) not in sys.path:
            sys.path.insert(0, str(_utils_dir))
        from logging_utils import log_execution
        log_execution(f"Error during migration: {e}", status='error')
        raise


def _load_json(file_path: Path) -> Any:
    """Load JSON file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _load_yaml(file_path: Path) -> Any:
    """Load YAML file"""
    with open(file_path, 'rb') as f:
        return tomllib.load(f)


def _find_matching_metrics(action_file: Path, metrics_files: List[Path]) -> Any:
    """Find metrics file matching an action_result file by timestamp"""
    # Extract timestamp from action file name (format: action_result_YYYY-MM-DD-HHMMSS.json)
    action_timestamp = action_file.name.replace('action_result_', '').replace('.json', '')

    for metrics_file in metrics_files:
        metrics_timestamp = metrics_file.name.replace('metrics_', '').replace('.yml', '')
        if action_timestamp == metrics_timestamp:
            return _load_yaml(metrics_file)

    return None


def _aggregate_older_attempts(
    older_action_files: List[Path],
    history_dir: Path,
    metrics_files: List[Path]
) -> None:
    """Aggregate older attempts into summary files"""
    agg_metrics = {
        'total_runs': len(older_action_files),
        'total_passed': 0,
        'total_failed': 0
    }

    for action_file in older_action_files:
        action_data = _load_json(action_file)
        metrics_data = _find_matching_metrics(action_file, metrics_files)

        if metrics_data and metrics_data.get('passed_runs'):
            agg_metrics['total_passed'] += metrics_data.get('passed_runs', 0)
            agg_metrics['total_failed'] += (metrics_data.get('total_runs', 0) - metrics_data.get('passed_runs', 0))

    if agg_metrics['total_runs'] > 0:
        agg_metrics['pass_rate'] = (
            agg_metrics['total_passed'] / (agg_metrics['total_passed'] + agg_metrics['total_failed'])
            if (agg_metrics['total_passed'] + agg_metrics['total_failed']) > 0
            else 0.0
        )

    agg_file = history_dir / 'aggregated_metrics.json'
    with open(agg_file, 'w', encoding='utf-8') as f:
        json.dump(agg_metrics, f, indent=2)


def main():
    """Main entry point for migration"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate learning files to new organized structure')
    parser.add_argument(
        'learnings_dir',
        help='Path to learnings directory to migrate (or "all" to migrate all RAVL loops)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    if args.learnings_dir == 'all':
        # Find all RAVL loops and migrate them
        ravl_root = Path.cwd() / 'ravl_loops'
        if not ravl_root.exists():
            print(f"✗ ravl_loops directory not found at {ravl_root}")
            return 1

        loop_dirs = list(ravl_root.rglob('learnings'))
        print(f"Found {len(loop_dirs)} learning directories to migrate")

        for learnings_dir in loop_dirs:
            migrate_learning_directory(learnings_dir, dry_run=args.dry_run)

        print(f"\n✓ Migration {'dry-run' if args.dry_run else ''} complete")
    else:
        learnings_dir = Path(args.learnings_dir)
        migrate_learning_directory(learnings_dir, dry_run=args.dry_run)
        print(f"\n✓ Migration {'dry-run' if args.dry_run else ''} complete")

    return 0


if __name__ == '__main__':
    sys.exit(main())
