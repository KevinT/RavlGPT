# RAVL Examples

This parent loop lists all working RAVL example loops.

## Available Examples

Examples demonstrate various RAVL patterns and capabilities:
- **communication_learner**: Advanced learning loop optimizing communication
- **example_1_simple_loop_tree**: Two simple loops using different LLM providers, with a parent that simply starts its children
- **example_2_intelligence_loop**: Track Springbok rugby team performance
- **example_3_recursive_learning_loop**: Environment explorer with recursive learning
- **example_4_python_loop**: Simpe RAVL loop in Python
- **github_trending_tracker**: Python loop tracking GitHub trending repos
- **tech_news_curator**: Markdown loop curating top tech news
- **tech_news_dashboard**: Parent orchestrator coordinating 3 news sources

## How to Use Examples

If you run an example it will be cloned locally, not run directly. To run an example:

```bash
ravl examples.<example_name>
```

Example:
```bash
ravl examples.example_1_simple_loop
```

This will clone the example to create a new loop in your current directory. You can clone any loop by using `--clone`.

