# Environment Explorer

A learning loop that discovers facts about its execution environment through exploration.

**Core Concept**: Start knowing nothing, progressively map your world through discovery.

---

# Reflect

## Current Knowledge

Check what you already know about your environment from previous explorations.
Your knowledge base is stored in the model - review it to avoid redundant exploration.

## Exploration Strategy

Based on your current knowledge, decide what aspect of the environment to explore next:

### Exploration Areas
- **Time & Context**: Current date, time, timezone, execution count
- **File System**: Directory structure, important files, project layout
- **System Info**: Operating system, Python version, available resources
- **Capabilities**: Available Python libraries, tools, commands
- **Patterns**: Recurring elements, interesting anomalies

### Decision Making

**If you're new (< 3 runs)**: Start with basics - time, location, immediate surroundings
**If you have basics (3-7 runs)**: Explore structure - directories, files, organization
**If you understand structure (7+ runs)**: Investigate interesting findings deeper

Choose ONE specific thing to explore this run. Be curious but focused.

---

# Act

## Explore Your Chosen Area

Based on your reflection, explore one aspect of your environment.

**Your exploration should**:
- Discover concrete facts (not generate or create)
- Document what you find clearly
- Focus on your chosen area

**Save your findings to**: `{loop learnings dir}/output/exploration_log.md` (append mode)

**Format your entry as**:
```
## Run {number} - {date}
**Exploring**: {what you chose to explore}
**Method**: {how you're investigating}

### Discoveries:
- {specific fact 1}
- {specific fact 2}
- {interesting observation}

### Significance:
{Why these discoveries matter or what they reveal}
```

Remember: You're an explorer mapping unknown territory. Each run adds to your map.

---

# Verify

## Evaluate Your Exploration

### Discovery Value (0-10)
- Did you learn something genuinely new?
- Or did you redundantly explore known territory?

### Insight Depth (0-10)
- Surface fact (file exists) = low score
- Deeper insight (pattern in file organization) = high score
- Connection between facts = highest score

### Exploration Efficiency (0-10)
- Did you make good use of this exploration?
- Could you have learned more with the same effort?

## Overall Score
(Discovery Value + Insight Depth + Exploration Efficiency) / 3

**Success Threshold**: 5.0 (You learned something worthwhile)

---

# Learn

## Update Your Knowledge Base

Add your discoveries to the model:

### Knowledge Map
Organize discovered facts by category:
- `environment.time`: Facts about when/how often you run
- `environment.location`: Where you exist in the filesystem
- `environment.structure`: Project organization, key directories
- `environment.capabilities`: What tools/libraries are available
- `environment.patterns`: Recurring themes or interesting anomalies

### Exploration History
Track what you've explored:
- `explored_areas`: List of what you've investigated
- `fully_mapped`: Areas you understand completely
- `worth_revisiting`: Areas with more to discover
- `dead_ends`: Areas that yielded nothing interesting

### Strategic Insights
Learn from your exploration patterns:
- `successful_strategies`: Approaches that yielded good discoveries
- `total_facts_discovered`: Running count of unique facts learned
- `most_interesting_finding`: The most significant discovery so far
- `hypotheses`: Ideas about what else might exist to explore

### Meta-Learning
Track your improvement as an explorer:
- `exploration_efficiency`: Are you getting better at choosing what to explore?
- `discovery_rate`: Facts discovered per run (should decrease over time as you map everything)
- `insight_quality`: Are your discoveries becoming more sophisticated?

## Reflection Prompt

As you update the model, consider:
- What patterns are emerging in your environment?
- Which exploration strategies work best?
- What unexplored territories remain?
- Are you ready to dig deeper into interesting findings?

---

# Success Indicators

You'll know this loop is working when:
1. **Your knowledge base grows** steadily in early runs
2. **Discovery rate naturally slows** as you map the environment
3. **Insights become more sophisticated** (from "file exists" to "project follows X pattern")
4. **Your exploration becomes strategic** rather than random
5. **The model shows clear learning** about both environment and exploration strategies

This is "Hello World" for learning loops - simple exploration that demonstrates:
- Starting with zero knowledge
- Building understanding through experience
- Strategic decision-making based on accumulated learning
- Natural progression from naive to sophisticated