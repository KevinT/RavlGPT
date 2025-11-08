#!/usr/bin/env python3
"""
Hello RAVL - Simplest Possible RAVL Loop

This example demonstrates the bare minimum RAVL implementation:
- REFLECT: Load previous model and observe current state
- ACT: Generate simple timestamped data
- VERIFY: Check that output was created
- LEARN: Update model with run statistics

No external APIs, no complexity - just the RAVL pattern.

Learning Objectives:
1. Understand the four RAVL phases
2. See model persistence in action
3. Learn how loops improve over time
4. Understand the learning file structure
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import sys

# Add framework common to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'common'))

from ravl_base import BaseRAVLLoop


class HelloRavlLoop(BaseRAVLLoop):
    """
    Minimal RAVL loop that generates timestamped greetings

    This loop demonstrates:
    - How models persist across runs
    - How verification works
    - How learning accumulates
    - The basic structure all RAVL loops follow
    """

    def __init__(self, loop_dir: Path):
        """Initialize the Hello RAVL loop"""
        learning_path = loop_dir / 'learnings' / 'loop_learning'
        model_path = learning_path / 'model.yml'
        super().__init__(model_path, "Hello RAVL", learning_path=learning_path)

        self.loop_dir = loop_dir
        self.output_path = loop_dir / 'output' / f'greetings_{datetime.now(timezone.utc).strftime("%Y-%m-%d")}.txt'

    def reflect(self) -> Dict[str, Any]:
        """
        PHASE 1: REFLECT

        Observe the current state and load previous learning.
        In this simple example, we just note whether we've run before.
        """
        print("\n" + "="*80)
        print(" Step 1 of 4: [R]EFLECT")
        print("="*80)

        # Load previous model
        model = self.load_model_with_timestamp(self._default_model)

        total_runs = model.get('total_runs', 0)
        last_run = model.get('last_run_timestamp', 'never')

        print(f"\n📊 Previous State:")
        print(f"   Total runs: {total_runs}")
        print(f"   Last run: {last_run}")

        # Create reflection summary
        reflection = {
            'previous_model': model,
            'is_first_run': total_runs == 0,
            'total_previous_runs': total_runs,
            'current_timestamp': datetime.now(timezone.utc).isoformat()
        }

        if reflection['is_first_run']:
            print("\n💡 This is our first run! Let's create our first greeting.")
        else:
            print(f"\n💡 We've run {total_runs} times before. Let's create another greeting!")

        return reflection

    def act(self, reflection: Dict[str, Any]) -> Dict[str, Any]:
        """
        PHASE 2: ACT

        Take action based on reflection. Generate a greeting and save it.
        """
        print("\n" + "="*80)
        print(" Step 2 of 4: [A]CT")
        print("="*80)

        # Generate greeting
        run_number = reflection['total_previous_runs'] + 1
        timestamp = datetime.now(timezone.utc)

        greeting = f"Hello from RAVL! (Run #{run_number} at {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')})"

        print(f"\n✍️  Generating greeting:")
        print(f"   {greeting}")

        # Save greeting to output file
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.output_path, 'a') as f:
            f.write(greeting + '\n')

        print(f"\n💾 Saved to: {self.output_path}")

        return {
            'greeting': greeting,
            'run_number': run_number,
            'timestamp': timestamp.isoformat(),
            'output_file': str(self.output_path)
        }

    def verify(self, reflection: Dict[str, Any], action_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        PHASE 3: VERIFY

        Check that our action succeeded. Verify the output file exists.
        """
        print("\n" + "="*80)
        print(" Step 3 of 4: [V]ERIFY")
        print("="*80)

        # Check output file exists
        output_exists = self.output_path.exists()

        # Check file has content
        file_size = self.output_path.stat().st_size if output_exists else 0

        # Determine if verification passed
        passed = output_exists and file_size > 0

        verification = {
            'passed': passed,
            'checks': {
                'output_file_exists': output_exists,
                'output_file_has_content': file_size > 0,
                'output_file_size': file_size
            },
            'message': 'All checks passed! ✅' if passed else 'Verification failed ❌'
        }

        print(f"\n🔍 Verification Results:")
        print(f"   Output file exists: {'✅' if output_exists else '❌'}")
        print(f"   Output has content: {'✅' if file_size > 0 else '❌'} ({file_size} bytes)")
        print(f"\n{verification['message']}")

        return verification

    def learn(self, reflection: Dict[str, Any], action_result: Dict[str, Any],
              verification: Dict[str, Any]) -> None:
        """
        PHASE 4: LEARN

        Update our model based on what happened. Track statistics about runs.
        """
        print("\n" + "="*80)
        print(" Step 4 of 4: [L]EARN")
        print("="*80)

        # Load previous model
        model = reflection['previous_model']

        # Update run statistics
        total_runs = model.get('total_runs', 0) + 1
        successful_runs = model.get('successful_runs', 0) + (1 if verification['passed'] else 0)
        failed_runs = model.get('failed_runs', 0) + (0 if verification['passed'] else 1)

        # Update model
        updated_model = {
            'total_runs': total_runs,
            'successful_runs': successful_runs,
            'failed_runs': failed_runs,
            'last_run_timestamp': action_result['timestamp'],
            'success_rate': successful_runs / total_runs if total_runs > 0 else 0,
            'metadata': {
                'last_greeting': action_result['greeting'],
                'last_output_file': action_result['output_file']
            }
        }

        print(f"\n📈 Updated Statistics:")
        print(f"   Total runs: {updated_model['total_runs']}")
        print(f"   Successful: {updated_model['successful_runs']}")
        print(f"   Failed: {updated_model['failed_runs']}")
        print(f"   Success rate: {updated_model['success_rate']:.1%}")

        # Save updated model
        self._save_model_with_timestamp(updated_model)

        print(f"\n💾 Model saved to learnings/loop_learning/")

    def _default_model(self) -> Dict[str, Any]:
        """Return default model structure for first run"""
        return {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'last_run_timestamp': None,
            'success_rate': 0.0,
            'metadata': {}
        }

    def _save_model_with_timestamp(self, model: Dict[str, Any]) -> None:
        """Save model with timestamp to learning directory"""
        from utils.file_utils import save_yaml_file

        # Save to timestamped file
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M%S')
        timestamped_path = self.learning_path / f'model-{timestamp}.yml'

        save_yaml_file(timestamped_path, model)

        # Also save to model.yml for convenience
        save_yaml_file(self.model_path, model)


def main():
    """Run the Hello RAVL loop"""
    loop_dir = Path(__file__).parent
    loop = HelloRavlLoop(loop_dir)

    # Execute RAVL cycle
    print("\n🚀 Starting Hello RAVL Loop")
    print("="*80)

    reflection = loop.reflect()
    action_result = loop.act(reflection)
    verification = loop.verify(reflection, action_result)
    loop.learn(reflection, action_result, verification)

    print("\n" + "="*80)
    if verification['passed']:
        print("✅ Hello RAVL Loop completed successfully")
    else:
        print("❌ Hello RAVL Loop completed with errors")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
