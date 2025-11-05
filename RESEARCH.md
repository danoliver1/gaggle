# Gaggle Research & Technical Implementation

## Existing Research on AI Scrum Teams

### Multi-agent Scrum Simulations
Multi-agent systems have been used to simulate scrum environments where teams with varying member capabilities work on delivering user stories consisting of multiple tasks with varying complexities across multiple sprints.

### Role-based Agent Frameworks
Recent frameworks use collaborative processes involving four agents: product owner (generates user stories and initiates prioritisation), QA agent (assesses story quality and identifies risks), developer (prioritises based on technical feasibility), and manager.

### Agile-specific Implementations
AgileCoder assigns Agile roles such as Product Manager and Scrum Master to facilitate sprint-based collaboration and development cycles, whilst AgileGen enhances Agile practices with human-AI collaboration using Gherkin language for testable requirements.

## Strands-Based Scrum Team Architecture

Reference implementation: `example.py`

### Key Optimisations for Parallelism and Efficiency

#### 1. Parallelism through Scrum
By operating sub-agents in parallel with their own context windows, you enable separation of concerns where distinct tools, prompts, and exploration trajectories reduce path dependency:

- Multiple developers work on independent tasks simultaneously
- QA can test multiple features in parallel
- Tech Lead identifies parallelisation opportunities upfront

#### 2. Token Efficiency
- Product Owner & Scrum Master use inexpensive models (Haiku)
- Tech Lead uses mid-tier to generate reusable code/components once
- Developers use expensive models but work in parallel to reduce wall-clock time
- Store generated tools/patterns for reuse across sprints

#### 3. Iterative Improvement
- Sprint retrospectives let agents learn what worked
- Tech Lead can optimise task breakdown over time
- Reusable components reduce token spend in future sprints

#### 4. Realistic Agile Process
Frameworks like AgileCoder incorporate iterative development, continuous feedback loops, and collaborative sprints.

## Implementation with Strands

Strands provides exactly what's needed:

✅ **Agents-as-tools pattern** - PO can call tech lead, tech lead calls developers  
✅ **Workflow orchestration** - Sprint ceremonies as coordinated workflows  
✅ **Parallel execution** - Multiple developers working simultaneously  
✅ **Different models per agent** - Cost optimisation by role  
✅ **State management** - Track sprint board, backlog, velocity  

This approach is genuinely innovative! You're not just parallelising tasks—you're simulating the entire feedback loop that makes Agile work, with specialised agents optimised for cost and speed. The sprint structure naturally creates the parallelisation opportunities needed.

## Cost & Efficiency Benefits

### Team Composition
- 1 Tech Lead (Opus) - $$$
- 3-5 Developers (Sonnet) - $$
- 1 QA (Sonnet) - $$
- 1 PO + 1 SM (Haiku) - $

### Token Efficiency Strategy
- **Tech Lead upfront investment:** Uses Opus to create reusable utilities once → Devs use these all sprint
- **Parallel development:** 5 Sonnet agents working simultaneously beats 1 Opus working sequentially
- **Clever reviews:** Tech Lead only reviews final code, not every iteration
- **Inexpensive coordination:** PO and SM handle ceremonies without burning expensive tokens

### Performance Metrics
Real-world parallel workflows show teams cap at 4-6 parallel tasks per lane and achieve **36% improvement** with parallelisation whilst maintaining similar quality (Skywork research).