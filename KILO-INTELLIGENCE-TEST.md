# Kilo Intelligence Test Suite

**Purpose:** Test Kilo's problem-solving, complex reasoning, and knowledge integration

**Date:** 2026-01-31

---

## Test Categories

1. **K3s Problem Diagnosis** - Can Kilo identify and plan fixes for cluster issues?
2. **Cross-Service Reasoning** - Can Kilo connect data from multiple services?
3. **Library of Truth Integration** - Does Kilo use stored knowledge effectively?
4. **Multi-Step Problem Solving** - Can Kilo break down complex tasks?
5. **Thoughtful vs Perfunctory Answers** - Does Kilo provide deep insights?

---

## Test 1: Fake Pod Crash (K3s Problem)

### Scenario
We'll simulate a pod crash and see if Kilo can diagnose and fix it.

### Setup
```bash
# Create fake crash scenario
ssh kilo@192.168.68.56 'sudo kubectl scale deployment kilo-reminder -n kilo-guardian --replicas=0'
```

### Expected Diagnosis
- Detect reminder service is down
- Identify that other services depend on reminders (habits, meds)
- Propose fix: scale back to 1 replica
- Consider impact: users won't get medication reminders

### Test Questions
1. "Kilo, check the K3s cluster and tell me if anything is wrong"
2. "What services are affected by this issue?"
3. "How would you fix this?"
4. "What's the priority of fixing this vs other potential issues?"

### Correct Fix
```bash
sudo kubectl scale deployment kilo-reminder -n kilo-guardian --replicas=1
```

---

## Test 2: Resource Exhaustion (Complex K3s)

### Scenario
Simulate memory pressure causing pod evictions

### Setup
```bash
# Scale up a service to create resource pressure (simulated)
# We won't actually do this, just ask Kilo to imagine the scenario
```

### Test Question
"Kilo, imagine the financial service pod keeps getting evicted with 'OOMKilled' status. The pod has a memory limit of 256Mi.

Looking at recent data:
- Financial service processes 100+ transactions per day
- It stores transaction history in memory
- Budget calculations happen every hour
- Month-end reports are very resource intensive

What's happening and how would you fix it? Consider:
1. Why is this happening?
2. Short-term fix to keep it running
3. Long-term architectural improvement
4. Trade-offs of each solution"

### Expected Answer Quality
**Good answer includes:**
- Diagnosis: Memory leak or insufficient limits
- Short-term: Increase memory limit to 512Mi
- Long-term: Implement database pagination, cache eviction
- Trade-offs: Cost vs reliability vs complexity

**Bad answer:**
- Just "increase the memory limit" without analysis
- No consideration of root cause
- No discussion of trade-offs

---

## Test 3: Cross-Service Reasoning

### Scenario
Test Kilo's ability to connect data across services

### Test Question
"Kilo, I've been overspending on food lately. Can you:
1. Check my food budget status
2. Look at my meal reminders
3. Check if I'm completing my 'meal prep' habit
4. Tell me if there's a pattern

Think about the relationships:
- If I don't meal prep → more eating out → higher food spending
- My reminders might not be at the right times
- My habits tracking shows if I'm actually doing what I planned

Give me a thoughtful analysis of what's happening and what I should change."

### Expected Answer Quality
**Good answer:**
- Checks financial service for food spending
- Checks reminder service for meal-related reminders
- Checks habits service for meal prep completion
- Identifies correlation: "I see you haven't completed meal prep habit in 10 days, and your food spending increased by 40% in that period"
- Proposes integrated solution: "Set earlier meal prep reminder + track grocery shopping habit + set weekly budget check-in"

**Bad answer:**
- Only checks one service
- Doesn't identify correlation
- Generic advice like "just spend less"

---

## Test 4: Library of Truth Integration

### Scenario
Test if Kilo uses stored knowledge to augment answers

### Setup
First, check what's in Library of Truth:
```bash
ssh kilo@192.168.68.56 'curl -s http://10.43.173.215:9006/books'
```

### Test Question
"Kilo, I'm interested in learning about [topic from available books].

Can you:
1. Search your knowledge base for information
2. Summarize what you find
3. Connect it to something relevant in my life (based on my habits, reminders, or spending)

For example, if there's content about productivity, relate it to my habit tracking. If there's financial advice, relate it to my budget situation."

### Expected Answer Quality
**Good answer:**
- Actually searches Library of Truth
- Cites specific passages
- Makes relevant connections to user's data
- Synthesizes knowledge + personal data

**Bad answer:**
- Generic knowledge without using library
- No citations
- No personal connections

---

## Test 5: Multi-Step Problem Solving

### Scenario
Test Kilo's ability to break down complex tasks

### Test Question
"Kilo, I want to save $500 next month for a vacation.

Looking at my current situation:
- Monthly income: Check financial service
- Current spending by category: Check budgets
- Current savings rate: Calculate from financial data
- Habits that affect spending: Check habits service

Create a detailed plan that:
1. Analyzes where my money currently goes
2. Identifies realistic areas to cut
3. Proposes specific habit changes
4. Sets up reminders to help me stay on track
5. Explains how to track progress

Be specific - use actual data from my services, not generic advice."

### Expected Answer Quality
**Good answer:**
- Pulls real data from all relevant services
- Specific numbers: "You spent $750 on food last month"
- Actionable cuts: "Reduce food budget from $750 to $500"
- Habit recommendations: "Meal prep 3x/week saves ~$30/week"
- Creates actual reminders
- Shows math: "$500 food + $100 streaming = $600 savings"

**Bad answer:**
- Generic "cut spending" advice
- No actual data
- No specific plan
- Doesn't create reminders or habits

---

## Test 6: Thoughtful Analysis

### Scenario
Test depth of reasoning vs surface-level responses

### Test Question
"Kilo, I've noticed I'm not completing my exercise habit, but I always complete my 'check social media' habits. Why do you think that is, and what does it say about how I should design my habit system?

Think about:
- Human psychology and motivation
- Habit formation theory
- My specific patterns (check my habit completion data)
- How to redesign habits to work WITH my nature, not against it"

### Expected Answer Quality
**Good answer:**
- References actual completion data
- Discusses instant gratification vs delayed rewards
- Proposes habit stacking: "Do 10 pushups BEFORE checking social media"
- Suggests starting smaller: "5 min exercise instead of 60 min"
- Shows understanding of human behavior

**Bad answer:**
- "Just try harder"
- No psychological insight
- No data analysis
- Generic motivation speech

---

## Test 7: Inter-Service Knowledge Building

### Scenario
Test if Kilo can learn from one service to improve another

### Test Question
"Kilo, I want you to analyze my medication adherence (meds service) and create insights (ML service) about when I'm most likely to forget. Then:

1. Check my medication taking patterns
2. Cross-reference with my habits and reminder completions
3. Identify times of day or situations where I forget
4. Generate a predictive insight: 'User is 80% more likely to forget evening meds on weekends'
5. Propose proactive interventions

This requires you to:
- Pull data from meds service
- Analyze patterns (ML engine should help)
- Create actionable insights
- Store learning in memory for future reference"

### Expected Answer Quality
**Good answer:**
- Actual data analysis
- Identifies specific patterns: "You miss evening meds 70% of the time on Fridays"
- Proposes targeted fix: "Extra reminder on Friday at 8pm with different sound"
- Explains reasoning: "Friday is social night, you're often out"
- Stores insight for future use

**Bad answer:**
- No data analysis
- Generic reminder suggestion
- No pattern identification
- Doesn't save learning

---

## Test 8: K3s Networking Issue

### Scenario
More complex K3s problem requiring system knowledge

### Test Question
"Kilo, the frontend can't reach the financial service. When I try to check my spending in the dashboard, it says 'Service Unavailable'.

Help me debug this:
1. Is the financial pod running?
2. Is the service endpoint exposed?
3. Is the gateway routing correctly?
4. Are there any network policies blocking it?
5. What's the specific failure point?

Give me commands to run to diagnose each step, and explain what each command tells us."

### Expected Answer Quality
**Good answer:**
- Step-by-step diagnostic process
- Specific kubectl commands:
  ```bash
  kubectl get pods -n kilo-guardian -l app=kilo-financial
  kubectl get svc -n kilo-guardian kilo-financial
  kubectl logs -n kilo-guardian deploy/kilo-gateway --tail=50
  ```
- Explanation of what each shows
- Logical troubleshooting flow
- Correct fix procedure

**Bad answer:**
- "Restart the pod"
- No diagnostic steps
- No explanation
- Doesn't identify root cause

---

## Test 9: Ethical/Priority Decision

### Scenario
Test Kilo's judgment and priority reasoning

### Test Question
"Kilo, I have $200 left in my budget for the month. I need to decide between:

A) Restocking my ADHD medication ($150) - I have 3 days left
B) Paying my streaming services ($100) to avoid cancellation
C) Buying groceries ($200) - I have 5 days of food left

I can only do one. What should I do and why?

Consider:
- Health impact
- Financial impact (late fees, reconnection fees)
- Alternative solutions
- Long-term vs short-term thinking

Give me a thoughtful analysis, not just an obvious answer."

### Expected Answer Quality
**Good answer:**
- Prioritizes medication (health > entertainment)
- Explains consequences of each choice clearly
- Suggests creative solutions: "Buy medication ($150), use $50 for minimal groceries, cancel non-essential streaming"
- Long-term: "Set up medication auto-refill, budget better for essentials"
- Shows empathy and understanding

**Bad answer:**
- Just picks one without analysis
- Doesn't explain trade-offs
- No creative solutions
- Judgmental tone

---

## Test 10: Learning and Memory

### Scenario
Test if Kilo retains and applies learned information

### Phase 1: Teaching
"Kilo, remember this: I have a standing coffee date with my friend every Tuesday at 2pm. This costs me about $5-10 each time. It's important to me for social connection, so I don't want to cut it from my budget."

### Phase 2: Testing (Later)
"Kilo, I'm trying to reduce my food/restaurant spending. What should I cut?"

### Expected Answer Quality
**Good answer:**
- Remembers Tuesday coffee date
- Doesn't suggest cutting it
- Proposes other cuts while preserving social time
- Shows memory of user's values

**Bad answer:**
- Forgets the information
- Suggests cutting coffee dates
- Generic suggestions
- No personalization

---

## How to Run These Tests

### Method 1: Via Chat Interface
1. Open: `http://192.168.68.56:30002`
2. Type each test question
3. Evaluate responses
4. Document results

### Method 2: Via Agent API
```bash
curl -X POST http://192.168.68.56:9200/agent/command \
  -H "Content-Type: application/json" \
  -d '{"command":"<test question here>"}'
```

### Method 3: Via AI Brain Direct
```bash
ssh kilo@192.168.68.56
curl -X POST http://10.43.63.197:9004/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user": "test",
    "message": "<test question here>",
    "context": {}
  }'
```

---

## Evaluation Rubric

### Problem Solving (1-5)
- 1: Can't identify problem
- 3: Identifies but can't fix
- 5: Diagnoses, fixes, prevents recurrence

### Cross-Service Reasoning (1-5)
- 1: Only checks one service
- 3: Checks multiple but doesn't connect them
- 5: Synthesizes data across services with insights

### Thoughtfulness (1-5)
- 1: Perfunctory, generic answers
- 3: Some analysis but shallow
- 5: Deep, nuanced, considers trade-offs

### Knowledge Integration (1-5)
- 1: Doesn't use Library of Truth or stored knowledge
- 3: Uses it but doesn't synthesize well
- 5: Seamlessly integrates knowledge + personal data

### Learning/Memory (1-5)
- 1: Forgets everything
- 3: Remembers but doesn't apply
- 5: Learns, remembers, applies proactively

---

## Current Known Limitations

Based on the system architecture:

1. **Library of Truth** requires manual parsing (`POST /parse_books`)
2. **ML Engine** might not be fully integrated with chat
3. **Memory system** exists but might not be in RAG loop
4. **Agent commands** currently route to simple service queries, not full AI reasoning

---

## Improvements Needed for Complex Thinking

### 1. Enhanced Agent Brain
Add tools for:
- Multi-service queries
- Pattern analysis
- Predictive insights
- Memory storage/retrieval

### 2. Library of Truth Integration
- Auto-parse books on startup
- Add semantic search (not just keyword)
- Citation system in responses

### 3. ML Engine Connection
- Expose pattern detection endpoints
- Integrate with chat for insights
- Predictive modeling for habits/spending

### 4. Memory Enhancement
- Store user preferences
- Remember previous solutions
- Learn from interactions

### 5. Inter-Service Orchestration
- Create "Jr Kilo" - simpler agent that monitors and feeds insights
- Knowledge graph connecting all services
- Automated insight generation

---

**This test suite will reveal:**
- What Kilo can currently do
- Where the intelligence gaps are
- What needs to be built to achieve complex thinking

**Let's run these tests and see how Kilo performs!**

---

Back to [[AGENT-CHAT-INTEGRATION|Integration Guide]]
