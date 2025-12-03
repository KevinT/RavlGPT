import os
import json
from pathlib import Path
from datetime import datetime

def main():
    print("🚀 Starting empty loop template execution...")
    
    # Get loop directories from environment (set by framework)
    learnings_dir = Path(os.environ.get('RAVL_LEARNINGS_DIR'))
    loop_dir = Path(os.environ.get('RAVL_LOOP_DIR'))
    
    print(f"📂 Learnings directory: {learnings_dir}")
    print(f"📂 Loop directory: {loop_dir}")
    
    # Create data directory if it doesn't exist
    data_dir = learnings_dir / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Data directory prepared: {data_dir}")
    
    # Generate sample data
    print("📊 Generating sample data...")
    sample_data = [
        {
            "id": "item_1",
            "data": {
                "name": "Sample Item 1",
                "timestamp": datetime.now().isoformat(),
                "description": "This is a placeholder data item from the empty loop template"
            }
        },
        {
            "id": "item_2",
            "data": {
                "name": "Sample Item 2",
                "timestamp": datetime.now().isoformat(),
                "description": "Replace this with your actual domain logic"
            }
        },
        {
            "id": "item_3",
            "data": {
                "name": "Sample Item 3",
                "timestamp": datetime.now().isoformat(),
                "description": "Customize this template for your use case"
            }
        }
    ]
    
    # Save results to JSON file
    output_file = data_dir / 'results.json'
    print(f"💾 Saving results to: {output_file}")
    
    with open(output_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"✅ Successfully saved {len(sample_data)} items to {output_file}")
    print("🎉 Empty loop template execution completed!")
    
    # Print summary
    print("\n📋 Summary:")
    print(f"   - Items generated: {len(sample_data)}")
    print(f"   - Output file: {output_file.relative_to(learnings_dir.parent)}")
    print(f"   - File size: {output_file.stat().st_size} bytes")
    print("\n💡 Next steps:")
    print("   1. Customize the ACT instructions in your loop's act.md file")
    print("   2. Update verification criteria in act.md")
    print("   3. Implement your domain-specific logic in place of sample data generation")

if __name__ == "__main__":
    main()