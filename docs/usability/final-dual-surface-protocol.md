# ResearchForge Final Web + n8n Evaluation Protocol

Status: **FROZEN / PREPARED / NOT RUN**  
Protocol version: `final-dual-surface-v1.0-frozen`  
Completed real-human sessions: **0**  
Human usefulness: **UNVALIDATED**

Do not recruit or run sessions until Phase 5 engineering, screenshots, CI, Docker and E2E are
green on the frozen candidate. Once the first real session begins, tasks, cases, metrics,
thresholds and denominator rules below cannot be changed.

## Participants and allocation

Recruit at least six consenting target users from individual researchers, finance learners and
junior researchers. Exclude the implementer, anyone who has seen the answers, AI personas and
automated test agents.

- Group A: Web with CATL 2024H1, then n8n with BYD 2024H1.
- Group B: n8n with CATL 2024H1, then Web with BYD 2024H1.
- Allocate alternately so group sizes differ by no more than one.
- Use the same question on both cases: `2024 年上半年利润是否真正转化成了经营现金流?`

This balances order and company exposure while keeping period and task equivalent. CATL 2024FY
remains a demo/generalization case and is not inserted mid-study.

## Session sequence

1. Give the final privacy notice; obtain consent before collecting observations.
2. Assign a pseudonym and preallocated A/B order. Do not collect direct identity.
3. Read the neutral task sheet. Do not point to interface controls or report sections.
4. Let the participant complete the first surface, then answer the shared questions aloud.
5. Reset to the start surface and repeat with the second assigned company.
6. On n8n only, ask the participant to submit BYD `2024FY` and explain the refusal. This checks
   failure-path comprehension; it does not change the successful research task.
7. Ask the surface-specific questions and overall preference. Record help immediately as
   `assisted`, never as an independent pass.
8. Offer withdrawal and public-summary choices, then store the privacy-minimized record under the
   ignored `artifacts/usability/real-human/` directory.

## Observable shared outcomes

| Outcome | Independent pass evidence |
|---|---|
| successful task initiation | Selects the assigned company/period/question and starts without help |
| conclusion understanding | Accurately paraphrases the direction and scope of the conclusion |
| key financial fact discovery | Finds at least net income and operating cash flow, including period |
| calculation understanding | Identifies operating cash flow ÷ net income and explains the ratio |
| evidence discovery | Opens or identifies one official filing locator and its page |
| limitation/counter evidence discovery | Identifies a displayed caveat or conflicting signal |
| monitoring discovery | States one next-filing item and its trigger/review timing |
| trust-boundary understanding | Explains that Python owns numbers/formulas, evidence is sourced, and n8n is not a second research engine |

Outcome values are `independent_pass`, `assisted`, `failed` or `not_attempted`. Time is diagnostic,
not an acceptance metric.

## Surface-specific outcomes

Web: navigation, information hierarchy, progressive disclosure and report readability.

n8n: workflow-entry usability, run-status comprehension, asynchronous-waiting experience,
failure-path comprehension and perceived automation value. “Value” passes when the participant
can name a plausible repeated/external workflow use without believing n8n recalculates or verifies
finance.

## Frozen acceptance and reporting

Use the exact denominator and seven acceptance rules in
[`../contracts/v1.5/final-human-evaluation.md`](../contracts/v1.5/final-human-evaluation.md).
Only `independent_pass` counts. Include every eligible participant and both surface attempts.
Report participant count, group allocation, every rate, assistance, failures, abandonments,
withdrawals, qualitative themes and sample limitations. Do not tune thresholds after results.

A pass supports only: “in this bounded pilot, target users could use both local surfaces to inspect
verified research.” It does not establish investment value, full-market coverage or general human
usefulness.
