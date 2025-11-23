# Communication Style Learner

An intelligent loop that learns effective communication strategies through experimentation and multi-dimensional feedback.

**Advanced Concepts**: Exploration vs exploitation, multi-dimensional optimization, strategic adaptation, hypothesis formation.

---

# Reflect

## Review Your Learning Model

Examine what you've learned about effective communication from previous runs.
Your model tracks performance across multiple communication styles and dimensions.

## Strategic Decision Making

### Available Communication Styles

- **Technical**: Precise, formal, computer science terminology
- **Narrative**: Story-based, metaphor-driven explanations
- **Visual**: Diagram descriptions, spatial metaphors, visual language
- **Socratic**: Question-driven, leading to discovery
- **Practical**: Code examples, hands-on demonstrations
- **Analogical**: Comparisons to familiar concepts
- **Hybrid**: Combinations of above styles

### Strategy Selection

**Exploration vs Exploitation Tradeoff:**

Consider your learning trajectory:
- **Runs 1-5 (Exploration Phase)**: Try diverse styles to map the landscape
- **Runs 6-10 (Exploitation Phase)**: Focus on high-performing styles
- **Runs 11+ (Refinement Phase)**: Try sophisticated combinations or variations

**Decision Factors:**
1. **Coverage**: Which styles haven't been tried yet?
2. **Performance**: Which styles show promise?
3. **Variance**: Are results consistent or variable?
4. **Plateau Detection**: Have scores stopped improving?
5. **Hypothesis Testing**: Do you have theories to validate?

**Your Strategic Choice:**
Choose a style based on your current knowledge and strategy.
Document WHY you made this choice - this reasoning is part of your learning.

---

# Act

## Create Your Communication Piece

You will explain **"recursion in programming"** using your chosen style.

### Requirements

**Content Creation:**
- Write 2-3 paragraphs explaining recursion
- Stay true to your chosen style throughout
- Balance clarity with style adherence
- Include concrete examples if appropriate

**Save your explanation to:** `output/explanations/run_{number}_{style}.md`

**Format:**
```markdown
# Recursion Explained: {Style} Approach

**Run**: {number}
**Date**: {date}
**Style**: {chosen_style}
**Strategy**: {why you chose this style}

---

{Your 2-3 paragraph explanation of recursion}

---

**Meta-Notes**: {Any observations about creating this explanation}
```

### Style Guidelines

**Technical**: Use terms like "base case", "recursive call", "stack frame", "termination condition"
**Narrative**: Tell a story that embodies recursion (e.g., Russian dolls, mirror reflections)
**Visual**: Describe diagrams, trees, or spatial representations
**Socratic**: Pose questions that lead to understanding ("What if a function could call itself?")
**Practical**: Show actual code with clear examples
**Analogical**: Compare to everyday recursive situations (organizing folders, factorial in math)
**Hybrid**: Meaningfully combine elements from multiple styles

Remember: You're not just explaining recursion, you're learning which explanation styles work best.

---

# Verify

## Multi-Dimensional Evaluation

Score your explanation across four critical dimensions:

### Clarity (0-10)
Evaluate comprehension ease:
- **9-10**: Crystal clear, immediate understanding
- **7-8**: Clear with minor ambiguities
- **5-6**: Understandable with effort
- **3-4**: Confusing, requires re-reading
- **0-2**: Incomprehensible

Key questions:
- Is the core concept of recursion immediately graspable?
- Are base case and recursive case clearly distinguished?
- Would a beginner understand this?

### Engagement (0-10)
Evaluate reader interest:
- **9-10**: Captivating, memorable, delightful
- **7-8**: Interesting, holds attention well
- **5-6**: Adequate, neither boring nor exciting
- **3-4**: Dry, requires effort to stay focused
- **0-2**: Extremely boring or off-putting

Key questions:
- Would someone enjoy reading this?
- Does it spark curiosity about recursion?
- Is the tone appropriate and inviting?

### Completeness (0-10)
Evaluate conceptual coverage:
- **9-10**: All essential aspects covered perfectly
- **7-8**: Most aspects covered well
- **5-6**: Basic concept covered, missing nuances
- **3-4**: Important elements missing
- **0-2**: Fails to explain recursion properly

Key questions:
- Are base case and recursive case both explained?
- Is the "why use recursion" question addressed?
- Are limitations/pitfalls mentioned?

### Memorability (0-10)
Evaluate lasting impact:
- **9-10**: Unforgettable, will stick for years
- **7-8**: Very memorable, will remember tomorrow
- **5-6**: Somewhat memorable, might recall key points
- **3-4**: Forgettable, won't stick
- **0-2**: Instantly forgettable

Key questions:
- Is there a hook or memorable element?
- Will the reader remember this explanation?
- Does it create lasting mental models?

## Overall Score Calculation

**Overall Score** = (Clarity × 0.3 + Engagement × 0.2 + Completeness × 0.3 + Memorability × 0.2)

**Quality Thresholds:**
- **Score ≥ 8.0**: Excellent (professional quality)
- **Score ≥ 6.5**: Good (effective communication)
- **Score ≥ 5.0**: Pass (adequate explanation)
- **Score < 5.0**: Needs improvement

**Important**: Higher scores indicate better learning, not just passing. Track score progression!

---

# Learn

## Update Your Sophisticated Model

Your model should capture nuanced learning about communication effectiveness:

### Performance Tracking

**Overall Metrics:**
```yaml
performance:
  total_runs: {count}
  average_score: {mean of all scores}
  best_score: {highest score achieved}
  best_style: {style that achieved best score}
  improvement_rate: {score_improvement / runs}
  plateau_detected: {true if last 3 runs similar}
```

**Per-Style Analysis:**
```yaml
styles:
  {style_name}:
    attempts: {number of times tried}
    scores: [{list of scores}]
    average: {mean score}
    variance: {score variance}
    trend: {improving/declining/stable}
    best_score: {highest for this style}
    dimensions:
      clarity: {average clarity score}
      engagement: {average engagement}
      completeness: {average completeness}
      memorability: {average memorability}
```

### Strategic Learning

**Pattern Recognition:**
```yaml
patterns:
  high_performers:
    - {style}: {reason it works}
  low_performers:
    - {style}: {reason it struggles}
  surprising_results:
    - {unexpected finding}
```

**Hypothesis Formation:**
```yaml
hypotheses:
  active:
    - hypothesis: {theory about what might work}
      evidence_for: [{supporting observations}]
      evidence_against: [{contradicting observations}]
      tests_needed: {how to validate}

  validated:
    - {confirmed theories}

  refuted:
    - {disproven theories}
```

### Meta-Learning

**Strategic Evolution:**
```yaml
strategy_evolution:
  phase: {exploration/exploitation/refinement}
  decision_quality: {getting better at choosing?}
  exploration_efficiency: {finding good styles faster?}
  exploitation_effectiveness: {optimizing known good styles?}
```

**Insights:**
```yaml
insights:
  most_important_dimension: {clarity/engagement/completeness/memorability}
  style_combinations_that_work:
    - {hybrid description}
  audience_preferences: {what readers seem to value}
  personal_strengths: {styles you excel at}
```

### Next Run Planning

**Strategic Priorities:**
```yaml
next_run:
  priority: {explore_new/exploit_best/test_hypothesis/break_plateau}
  candidate_styles:
    - {style}: {reason to try}
  specific_goal: {what you want to learn}
```

## Reflection Questions

As you update your model, consider:

1. **Performance Patterns**: Are certain styles consistently superior?
2. **Dimension Tradeoffs**: Does improving one dimension hurt others?
3. **Hybrid Effectiveness**: Do combinations outperform pure styles?
4. **Plateau Breaking**: If stuck, what radically different approach could work?
5. **Audience Model**: What mental model of the "reader" are you developing?

---

# Success Indicators

Your learning is successful when:

1. **Scores improve** from ~5-6 (initial) to ~8-9 (sophisticated)
2. **Strategy evolves** from random to highly strategic
3. **Model shows insights** like "Visual + Practical beats pure Technical"
4. **Hypotheses form and test** showing scientific thinking
5. **Plateau recovery** demonstrates adaptive capabilities
6. **Meta-learning emerges** - you learn how to learn better

The ultimate success: Your model contains actionable wisdom about effective communication that could help humans communicate better.

---

## Advanced Challenge

Once you've mastered basic styles, try:
- **Audience-adapted styles**: Technical for experts, simple for beginners
- **Progressive disclosure**: Start simple, build complexity
- **Multi-modal**: Combine text with simulated diagrams
- **Cultural adaptation**: Vary metaphors for different contexts
- **Emotional resonance**: Add humor, wonder, or surprise

This loop demonstrates that RAVL isn't just about task automation - it's about creating intelligent systems that learn, adapt, and improve at complex, nuanced tasks.