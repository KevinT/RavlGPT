import os
from pathlib import Path

# Get loop directory from environment (set by framework)
loop_dir = Path(os.environ.get('RAVL_LOOP_DIR'))

# The examples directory is the current loop directory
examples_dir = loop_dir

print("=" * 80)
print("RAVL EXAMPLE LOOPS")
print("=" * 80)
print()

# Scan for all subdirectories that contain loop configuration
example_loops = []

for item in sorted(examples_dir.iterdir()):
    if not item.is_dir():
        continue
    
    # Skip hidden directories and special directories
    if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules']:
        continue
    
    # Check if this directory contains a RAVL loop configuration
    config_file = item / 'config' / 'ravl.toml'
    if not config_file.exists():
        continue
    
    # Check for child loops
    child_loops = []
    loops_subdir = item / 'loops'
    if loops_subdir.exists() and loops_subdir.is_dir():
        for child_item in sorted(loops_subdir.iterdir()):
            if child_item.is_dir() and not child_item.name.startswith('.'):
                child_config = child_item / 'config' / 'ravl.toml'
                if child_config.exists():
                    child_loops.append(child_item.name)
    
    example_loops.append({
        'name': item.name,
        'path': str(item.relative_to(examples_dir)),
        'has_children': len(child_loops) > 0,
        'children': child_loops
    })

# Display examples grouped by type
print("📚 AVAILABLE EXAMPLE LOOPS")
print()

# Categorize examples
single_loops = [ex for ex in example_loops if not ex['has_children'] and 'nested' not in ex['name'].lower() and 'orchestrat' not in ex['name'].lower()]
orchestrator_loops = [ex for ex in example_loops if ex['has_children'] or 'nested' in ex['name'].lower() or 'orchestrat' in ex['name'].lower()]

# Display single loops
if single_loops:
    print("🔹 SINGLE LOOP EXAMPLES")
    print("   (Simple, self-contained loops that demonstrate core RAVL functionality)")
    print()
    
    for example in single_loops:
        print(f"   • {example['name']}")
        print(f"     Path: {example['path']}")
        
        # Provide description based on name
        if 'single_loop' in example['name']:
            print(f"     Purpose: Basic single-loop example demonstrating the core RAVL cycle")
        elif 'python' in example['name']:
            print(f"     Purpose: Python-specific loop example showing language-specific patterns")
        elif 'analysis' in example['name']:
            print(f"     Purpose: Data analysis loop demonstrating analytical workflows")
        elif 'learning' in example['name']:
            print(f"     Purpose: Learning loop showing how RAVL accumulates knowledge over iterations")
        elif 'communication' in example['name']:
            print(f"     Purpose: Communication-focused loop for message processing or interaction patterns")
        elif 'tech_news' in example['name']:
            if 'curator' in example['name']:
                print(f"     Purpose: Tech news curation loop for collecting and organizing news content")
            elif 'dashboard' in example['name']:
                print(f"     Purpose: Tech news dashboard for displaying curated technology news")
            else:
                print(f"     Purpose: Tech news processing loop")
        elif 'github' in example['name'] and 'trending' in example['name']:
            print(f"     Purpose: GitHub trending tracker for monitoring popular repositories")
        else:
            print(f"     Purpose: Example demonstrating RAVL loop patterns")
        
        print()

# Display orchestrator/nested loops
if orchestrator_loops:
    print("🔸 ORCHESTRATOR / NESTED LOOP EXAMPLES")
    print("   (Parent loops that coordinate multiple child loops)")
    print()
    
    for example in orchestrator_loops:
        print(f"   • {example['name']}")
        print(f"     Path: {example['path']}")
        
        if 'nested' in example['name']:
            print(f"     Purpose: Demonstrates nested loop architecture with parent-child coordination")
        else:
            print(f"     Purpose: Orchestrator loop managing multiple child loops")
        
        if example['has_children']:
            print(f"     ⚠️  This example is part of a loop family with child loops:")
            for child in example['children']:
                print(f"        - {child}")
        
        print()

print("=" * 80)
print(f"TOTAL EXAMPLES FOUND: {len(example_loops)}")
print("=" * 80)
print()
print("💡 TIP: To run an example, use: ./ravl examples.<example_name>")
print("   Example: ./ravl examples.example_1_single_loop")
print()