# It All Boils Down to Two Things: Your Knowledge of Domains — and How Well You Can Ask Questions.

Not your Python skills. Not your SQL mastery. Not even your Tableau certifications.

In 2025, the moat in analytics isn't technical proficiency — it's **domain fluency** and **the precision of your prompts.**

Let me show you what I mean.

---

## What I Built — In One Day, With a $20 Subscription

I built a **full-stack, production-grade SCLC (Small Cell Lung Cancer) Patient Journey Analytics Dashboard**.

Not a mockup. Not a wireframe. A deployed, interactive platform with:

- Real-time KPI cards (patient volumes, time-to-treatment, IO uptake, trial enrollment)
- Time-to-treatment distribution analysis with clinical benchmarks
- First-line and second-line treatment pattern visualizations
- A geographic heatmap across all 50 US states
- A paginated patient-level data table with full clinical histories
- A qualitative **Insights & Interpretation engine** that auto-generates clinical signals from the data — flagging action items, care gaps, and strengths
- Synthetic but clinically realistic data modeled on real-world SCLC treatment pathways

**The stack:** React, TypeScript, Tailwind CSS, Recharts, Zustand, TanStack Query, FastAPI, PostgreSQL — deployed on GitHub Pages.

**The cost:** A $20/month Claude subscription.

**The time:** One working day.

No team. No sprint planning. No Jira tickets. One person, one AI, one day.

---

## But Here's What Actually Made It Work

It wasn't the AI that wrote the code. It was the questions I asked.

When I prompted for treatment patterns, I didn't say *"make a chart."* I said:

> *"First-line regimens should reflect NCCN guideline-concordant categories — platinum/etoposide backbone with atezolizumab or durvalumab arms, plus a clinical trial bucket. Second-line should include topotecan, lurbinectedin, CAV, and re-challenge platinum."*

When I asked for the Insights section, I didn't say *"add some analysis."* I said:

> *"Generate qualitative clinical signals — flag if IO uptake is below 60% against NCCN benchmarks, detect geographic TTT disparities, identify if 31+ day delays exceed 10% given SCLC's aggressive biology, and reference IMpower133/CASPIAN evidence for chemo-IO interpretation."*

**The AI is the engine. Domain knowledge is the steering wheel. The prompt is the road map.**

Without knowing what ECOG performance status means, what NCCN guidelines recommend, or why lurbinectedin's 2020 approval matters in a second-line context — no amount of AI tooling produces anything meaningful. You get a chart. You don't get insight.

---

## The Impact: How This Changes Every Dimension of Analytics Work

This isn't a cool demo. This is a fundamental shift in how analytics gets done. Here's what changes:

**1. Speed to Insight: Days → Hours**
What traditionally takes a cross-functional team 4-8 weeks — requirements, data modeling, ETL, dashboard dev, UAT — collapsed into a single day. The feedback loop between "I have a question" and "Here's the answer, visualized" is now measured in minutes.

**2. Prototyping Becomes the Product**
The line between "proof of concept" and "production" is vanishing. The prototype I built isn't a throwaway — it's deployed, interactive, and stakeholder-ready. This kills the "let me show you a PowerPoint of what the dashboard could look like" phase entirely.

**3. Domain Experts Become Builders**
The biggest shift. You no longer need to be a full-stack developer to build a full-stack application. If you understand the clinical pathway, the regulatory landscape, the business logic — you can build the tool. Analytics is no longer gatekept by engineering capacity.

**4. Synthetic Data Unlocks Compliant Innovation**
Healthcare analytics is paralyzed by data access timelines — IRB approvals, BAAs, de-identification, HIPAA reviews. Clinically realistic synthetic data lets you build, validate, and demo the entire analytical framework while the real data pipeline catches up. The compliance bottleneck becomes a parallel workstream, not a blocker.

**5. Qualitative Interpretation at Scale**
Dashboards traditionally stop at "here's the number." The Insights engine I built goes further — it interprets the number against clinical benchmarks, flags care gaps, and prioritizes actions. This is the layer that transforms a reporting tool into a **decision-support system.** And it's generated dynamically, not hardcoded.

**6. The Analyst's Role Elevates**
When the mechanical work — wrangling, coding, building, deploying — is compressed by AI, what's left is the work that actually matters: framing the right question, choosing the right benchmark, interpreting the result in context, and translating it into action. The analyst becomes a strategist.

**7. Democratization of Advanced Analytics**
A platform like this — with geographic analysis, treatment pathway mapping, and auto-generated clinical insights — would traditionally require a dedicated analytics engineering team plus a clinical informatics specialist. Now it requires one person who knows both the domain and how to communicate with AI effectively.

**8. Documentation and Knowledge Transfer Built-In**
Every prompt I wrote is a specification. Every AI response is a documented decision. The entire build process creates an auditable trail of clinical logic, design choices, and implementation rationale — something traditional development rarely produces this cleanly.

---

## What's Next: Scaling This Without Scaling the Cost

Here's the reality: a $20 subscription works brilliantly for a single-developer, single-project workflow. But at enterprise scale — where you have 15 dashboards, 8 data pipelines, real-time integrations, and a team of 20 — costs compound. Every complex prompt, every multi-file refactor, every large codebase interaction consumes tokens. And tokens cost money.

**That's why I'm now exploring [OpenCode](https://opencode.ai/).**

OpenCode is an open-source AI coding agent with 100,000+ GitHub stars and 2.5M+ monthly developers. Here's why it matters for enterprise-scale analytics:

- **75+ LLM providers** — connect Claude, GPT, Gemini, or run fully local models. You pick the right model for the right task at the right cost
- **Local model support** — for sensitive healthcare data, run everything on-premise. No data leaves your infrastructure. HIPAA compliance by architecture, not by policy
- **No vendor lock-in** — swap providers without rewriting a single workflow
- **Parallel multi-session operations** — run multiple agents simultaneously across different parts of your analytics stack
- **Zero storage of your code or context** — privacy-first by design, which matters when your prompts contain PHI-adjacent domain logic

The vision: **Claude's intelligence for complex clinical reasoning, paired with OpenCode's open infrastructure for cost-efficient, scalable, and privacy-compliant deployment.**

The $20 subscription proved the concept. Open-source infrastructure scales it.

---

## The Takeaway

The future of analytics doesn't belong to the person who writes the best SQL or builds the prettiest dashboard.

It belongs to the person who:
- **Understands the domain deeply enough** to know what questions matter
- **Communicates precisely enough** to turn those questions into actionable AI prompts
- **Thinks architecturally enough** to choose the right tools for scale

The tools are commoditizing. The knowledge isn't.

---

*Built with Claude AI. Deployed on GitHub Pages. Powered by domain knowledge and well-crafted questions.*

*If you're working at the intersection of healthcare analytics, AI-assisted development, or clinical data platforms — let's connect. The playbook is changing fast.*

#HealthcareAnalytics #AIinHealthcare #DataScience #ClaudeAI #OpenCode #SCLC #ClinicalAnalytics #PatientJourney #DigitalHealth #Analytics #ArtificialIntelligence #OpenSource #PromptEngineering
