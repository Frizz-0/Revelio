You're right. I was still framing **Revelio as a general-purpose agent with investigation as one capability**.

That is backwards.

**Revelio is an investigation system first.** The Agent is the mechanism that makes the investigation dynamic.

The architecture we should be targeting is closer to this:

```text
                              USER
                               │
                               ▼
                    ┌────────────────────┐
                    │   INVESTIGATION    │
                    │       GOAL         │
                    └─────────┬──────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │    INVESTIGATION       │
                  │       AGENT            │
                  │                        │
                  │ • Understand objective │
                  │ • Break down problem   │
                  │ • Form hypotheses      │
                  │ • Decide next action   │
                  │ • Evaluate evidence    │
                  │ • Detect gaps          │
                  │ • Verify claims        │
                  │ • Synthesize findings  │
                  └───────────┬────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              INVESTIGATION         CAPABILITIES
                 STATE                   │
                    │                    │
                    │          ┌─────────┼─────────┐
                    │          │         │         │
                    │          ▼         ▼         ▼
                    │       SEARCH    DOCUMENT   VISION
                    │          │         │         │
                    │       SearXNG   Fetch/OCR   VLM/CV
                    │
                    ▼
              ┌─────────────────┐
              │    EVIDENCE     │
              │     STORE       │
              │                 │
              │ Sources         │
              │ Claims          │
              │ Findings        │
              │ Contradictions  │
              │ Confidence      │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    ANALYSIS     │
              │                 │
              │ Compare         │
              │ Verify          │
              │ Identify gaps   │
              │ Test hypotheses │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    SYNTHESIS    │
              │                 │
              │ Answer          │
              │ Evidence        │
              │ Caveats         │
              │ Sources         │
              └─────────────────┘
```

### The key difference

The previous architecture was:

```text
Agent
 └── capabilities
      ├── search
      ├── calculator
      ├── research
      └── vision
```

That's a **general agent framework**.

What you're actually building is:

```text
Investigation Agent
       │
       ├── Investigation State
       ├── Evidence
       ├── Hypotheses
       ├── Findings
       ├── Verification
       ├── Gap Detection
       └── Capabilities
             ├── Search
             ├── Documents
             ├── Vision
             ├── Calculator
             └── ...
```

So **investigation is the system**, not merely a capability.

---

## The actual investigation loop

This is the part I think you were remembering:

```text
                    INVESTIGATION GOAL
                           │
                           ▼
                 ┌──────────────────┐
                 │ Understand        │
                 │ the question      │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Decompose into   │
                 │ sub-questions    │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Form hypotheses  │
                 └────────┬─────────┘
                          ▼
                 ┌──────────────────┐
                 │ Gather evidence  │◄────────────┐
                 └────────┬─────────┘             │
                          ▼                        │
                 ┌──────────────────┐             │
                 │ Analyze evidence │             │
                 └────────┬─────────┘             │
                          ▼                        │
                 ┌──────────────────┐             │
                 │ Are claims       │             │
                 │ sufficiently     │             │
                 │ supported?       │             │
                 └──────┬─────┬─────┘             │
                        │     │                   │
                       NO    YES                  │
                        │     │                   │
                        ▼     ▼                   │
                 ┌─────────┐ ┌──────────────┐     │
                 │ Identify│ │ Verify /     │     │
                 │ gaps    │ │ cross-check  │     │
                 └────┬────┘ └──────┬───────┘     │
                      │              │             │
                      └──────────────┘             │
                             │                     │
                       Need more evidence? ────────┘
                             │
                            NO
                             ▼
                       ┌───────────┐
                       │SYNTHESIZE │
                       └─────┬─────┘
                             ▼
                           ANSWER
```

**But** there is one important modernisation from our earlier design:

This shouldn't be implemented as 10 hardcoded sequential classes.

The **Investigation Agent controls the loop**.

For example:

```text
"Is NVIDIA's AI GPU dominance sustainable?"
```

could produce:

```text
Sub-question 1:
What is NVIDIA's current AI accelerator share?

Sub-question 2:
How has that share changed?

Sub-question 3:
What competitors/custom silicon exist?

Sub-question 4:
What constraints could reduce NVIDIA's position?
```

Then the Agent decides what evidence is needed for each.

It might do:

```text
Search
→ Analyze
→ Search
→ Analyze
→ Verify
→ Search competitor data
→ Compare
→ Calculate market-share change
→ Verify
→ Synthesize
```

Another investigation might need:

```text
Document
→ Vision
→ OCR
→ Analyze
→ Verify
→ Synthesize
```

The **investigation strategy is dynamic**.

---

# And this resolves your earlier concern

You asked:

> "Why are we adding a bunch of decisions for every file/capability?"

We shouldn't.

The Agent shouldn't have:

```text
if search → do X
if analyze → do Y
if verify → do Z
if calculator → do W
```

Instead it has a small number of **investigation-level decisions**:

```text
Do I understand the question?
Do I need more evidence?
Is this claim supported?
Is there a contradiction?
Is there an unresolved gap?
Is the investigation sufficient to answer?
```

Capabilities are simply how it obtains the information needed to answer those questions.

---

# Canonical Revelio architecture

So I'd freeze this as our conceptual architecture:

```text
                              REVELIO
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  INVESTIGATION AGENT   │
                    │                        │
                    │ Goal                   │
                    │ Decomposition          │
                    │ Hypotheses             │
                    │ Planning / Decisions   │
                    │ Evidence evaluation    │
                    │ Gap detection          │
                    │ Verification           │
                    │ Synthesis               │
                    └───────────┬────────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
        INVESTIGATION       CAPABILITY          MODEL
           STATE              LAYER              LAYER
             │                  │                  │
             │          ┌───────┼───────┐         │
             │          │       │       │         │
             │       Search  Document Vision      │
             │          │       │       │         │
             │       SearXNG   │      VLM/CV      │
             │                  │                  │
             ▼                  ▼                  ▼
        ┌────────────────────────────────────────────┐
        │              EVIDENCE / FINDINGS           │
        │                                            │
        │ Sources • Claims • Evidence • Findings     │
        │ Contradictions • Gaps • Confidence         │
        └──────────────────────┬─────────────────────┘
                               │
                               ▼
                         FINAL SYNTHESIS
                               │
                               ▼
                              USER
```

And **V1 is only the first vertical slice of this**, not the entire diagram.

```text
V1:

Investigation Goal
       ↓
Investigation Agent
       ↓
Search
       ↓
Evidence
       ↓
Analyze
       ↓
Verify
       ↓
Synthesize
       ↓
Answer
```

Then we progressively add:

```text
V1 → Search + evidence + analysis + verification
V2 → documents
V3 → vision
V4 → richer evidence/hypothesis management
V5 → multimodal investigations
```

That is much closer to what **Revelio** was supposed to be. The previous "general agent + research capability" framing was too generic.
