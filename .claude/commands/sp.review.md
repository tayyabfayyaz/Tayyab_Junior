---
description: Perform a spec-driven code review of current changes against spec.md, plan.md, tasks.md, and the project constitution. Produces a structured review report with a final verdict before committing or creating a PR.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

Accepted tokens (parsed from `$ARGUMENTS`):
- Positional: feature slug (e.g. `001-fte-task-executor`) — auto-detected from branch if omitted
- `--strict` — elevate all MEDIUM findings to HIGH
- `--focus <area>` — limit review to one pass: `constitution | requirements | tasks | architecture | security | quality`
- `--diff-base <ref>` — git ref to diff against (default: `HEAD`)
- `--debug` — print per-file analysis steps inline

---

## Goal

Review all current repository changes against the SDD artifact chain (`spec.md → plan.md → tasks.md → constitution.md`) and produce a structured, severity-graded review report with an explicit machine-readable verdict:

- **APPROVED** — zero findings
- **APPROVED_WITH_WARNINGS** — only MEDIUM/LOW findings
- **CHANGES_REQUIRED** — one or more HIGH findings
- **BLOCKED** — one or more CRITICAL findings

This skill is **strictly read-only**. It MUST NOT modify any file, create commits, or execute code from the diff.

---

## Operating Constraints

- **STRICTLY READ-ONLY**: Never write, modify, delete, or execute any file.
- **NO CODE EXECUTION**: Never run code from the diff, test runners, or build scripts.
- **DETERMINISTIC**: Re-running without changes MUST produce identical IDs, categories, and verdict.
- **CONSTITUTION AUTHORITY**: Constitution violations are always CRITICAL and cannot be downgraded.
- **FINDINGS CAP**: Maximum 50 findings total; summarize overflow.

---

## Execution Steps

### Phase 0: Argument Parsing

Parse `$ARGUMENTS`:

```
feature_slug = first positional word token (or null — auto-detect from branch)
strict_mode  = "--strict" flag present (boolean, default false)
focus_area   = word after "--focus" (default: "all")
diff_base    = word after "--diff-base" (default: "HEAD")
debug_mode   = "--debug" flag present (boolean, default false)
```

Validate:
- If `focus_area` is provided, it must be one of: `constitution | requirements | tasks | architecture | security | quality | all`. If invalid, default to `all` and warn.
- If `diff_base` is provided, verify it's a valid git ref: `git rev-parse --verify <ref>`. If invalid, abort with code E-U4.

---

### Phase 1: Context Bootstrap

**Step 1a — Resolve Feature Directory**

Run `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks` from repo root. Parse JSON to extract `FEATURE_DIR` and `AVAILABLE_DOCS`.

If the script fails or `FEATURE_DIR` is null:
- If `feature_slug` was provided, look for `specs/<feature_slug>/` directly
- If still not found, abort with error E-U3

**Step 1b — Verify SDD Artifacts**

Check that all three SDD artifacts exist:
- `FEATURE_DIR/spec.md` → SPEC
- `FEATURE_DIR/plan.md` → PLAN
- `FEATURE_DIR/tasks.md` → TASKS

If any artifact is missing, abort immediately:
```
❌ REVIEW BLOCKED — Missing Artifact

  Missing: <artifact>
  Fix:     Run /sp.<step> to generate the missing artifact.
           spec.md  → /sp.specify
           plan.md  → /sp.plan
           tasks.md → /sp.tasks
```

**Step 1c — Load Constitution**

Load `.specify/memory/constitution.md` → CONSTITUTION.

If not found: emit `[WARN][BOOTSTRAP] constitution.md not found — Pass A (Constitution) will be skipped`. Continue.

**Step 1d — Capture Git State**

```bash
git status --porcelain            # staged + unstaged changes
git diff HEAD --stat              # lines changed summary (fall back to --cached if HEAD fails)
git diff HEAD --name-only         # list of changed files
git log --oneline -5              # recent commit context
```

Parse CHANGED_FILES from `--name-only` output.

If CHANGED_FILES is empty AND `git status --porcelain` is also empty:
- Emit: `ℹ️ No code changes detected. Running artifact-only checks (Passes A, B, C).`
- Limit passes to A, B, C only.

---

### Phase 2: Artifact Ingestion

Load only the high-signal sections from each artifact (do not dump full content into analysis):

**From spec.md:**
- Functional Requirements (FR-N items)
- Non-Functional Requirements (NFR-N items)
- User Stories and Acceptance Criteria
- Success Criteria

**From plan.md:**
- Tech stack / technology decisions
- File/directory structure conventions
- Security model decisions
- Data model references
- External dependency list

**From tasks.md:**
- All task entries with their ID, description, status (`[X]` or `[ ]`), phase, and referenced file paths

**From constitution.md:**
- All six principles (I–VI) with their MUST statements

Build internal semantic models (never include raw artifact dumps in output):

```
REQUIREMENT_INVENTORY: { slug → { text, source, has_coverage:bool } }
TASK_MAP:              { task_id → { desc, files[], completed:bool, has_code_change:bool } }
ARCH_RULES:            { rule_id → { type, constraint, source_section } }
CONSTITUTION_RULES:    { principle_id → { name, musts:[], source_section } }
```

---

### Phase 3: Change Analysis

For each file in CHANGED_FILES:
1. Determine which task(s) reference this file (by matching path patterns in TASK_MAP)
2. Mark `has_code_change = true` on matched tasks
3. Correlate with requirements via keyword/concept matching

Detect:
- Files changed with NO matching task → candidate for finding T2
- Tasks marked `[X]` with NO changed files → candidate for finding T1

---

### Phase 4: Six Detection Passes

Run only the pass(es) matching `focus_area` (or all if `"all"`).

Each pass produces findings in this structure:
```
{id, category, severity, location, summary, recommendation}
```

Finding ID prefix by pass:
- Pass A → `C` (Constitution)
- Pass B → `R` (Requirement)
- Pass C → `T` (Task)
- Pass D → `A` (Architecture)
- Pass E → `S` (Security)
- Pass F → `Q` (Quality)

Increment the suffix integer per pass: C1, C2, R1, R2, T1…

#### Pass A — Constitution Compliance

For each MUST statement in each constitution principle (I–VI):

**Principle I (File-Based Task Execution):**
- Detect: executor or runner code acting on inline/hardcoded instructions rather than reading task files
- Flag: any code path that bypasses the task file lifecycle

**Principle II (MCP Tool Isolation):**
- Scan all changed files for direct HTTP calls to external services:
  - Python: `requests.get/post/put`, `urllib.request`, `httpx.get/post`
  - TypeScript/JS: `fetch(`, `axios.get/post`, `XMLHttpRequest`
- Flag any such call where the URL resolves to an external domain and the call is NOT inside a file under `mcp_server/` or equivalent MCP directory
- Severity: **CRITICAL**

**Principle III (Auditability & Transparency):**
- Detect: task state transitions without a corresponding log call in the same code block
- Detect: exception handlers that swallow errors silently (`except: pass`, `catch(e) {}` with empty body)
- Severity: **HIGH**

**Principle IV (Watcher-Driven Ingestion):**
- Detect: watcher service code that calls executor logic directly instead of writing task files
- Severity: **HIGH**

**Principle V (Memory-Augmented Reasoning):**
- Detect: executor code that calls Claude API / generates responses without first loading memory context
- Severity: **MEDIUM**

**Principle VI (Security by Default):**
- See Pass E for detailed security checks (Pass E handles security patterns)
- Detect: new endpoints added without authentication middleware reference
- Severity: **CRITICAL**

All constitution violations are CRITICAL unless explicitly noted above.

#### Pass B — Requirement Coverage

For each requirement in REQUIREMENT_INVENTORY:
1. Search CHANGED_FILES content for logical coverage signals (keywords, function names, API paths that map to the requirement)
2. Mark `has_coverage = true` if found

Flag requirements with `has_coverage = false`:
- Core functional requirement with zero coverage → **HIGH**
- Non-functional requirement with zero coverage → **MEDIUM**

Location: `spec.md:<requirement-id>`
Recommendation: Identify which task should implement this requirement.

#### Pass C — Task Completion Alignment

Detect:
1. Task marked `[X]` in tasks.md with `has_code_change = false`:
   - Summary: "Task marked complete but no code changes detected for its file references"
   - Severity: **MEDIUM**
   - Recommendation: Verify task is truly complete or un-mark [X]

2. CHANGED_FILES that have no matching task entry AND are not test/config/docs files:
   - Summary: "Code change detected with no corresponding task in tasks.md"
   - Severity: **HIGH**
   - Recommendation: Add task to tasks.md or verify the change is intentional

Skip this pass if tasks.md contains no checkbox markers.

#### Pass D — Architecture Drift

For each file in CHANGED_FILES that contains source code:
1. Detect imported libraries / frameworks (look for `import`, `require`, `from ... import` patterns)
2. Compare detected technologies against plan.md tech stack decisions
3. Flag any technology present in code but absent from plan.md

Also check:
- New directories created that contradict plan.md file structure section
- Database drivers/ORMs used that differ from plan.md data model decisions

Severity: **HIGH** for technology drift, **MEDIUM** for directory/naming drift.

#### Pass E — Security & Safety Boundaries

Scan all changed file content for:

| Pattern | Severity | Finding |
|---------|----------|---------|
| `API_KEY\s*=\s*["'][^"']{8,}` (literal assigned) | CRITICAL | Hardcoded API key |
| `password\s*=\s*["'][^"']{4,}` | CRITICAL | Hardcoded password |
| `token\s*=\s*["'][^"']{8,}` | CRITICAL | Hardcoded token |
| `secret\s*=\s*["'][^"']{8,}` | CRITICAL | Hardcoded secret |
| SQL string concatenation with user input | HIGH | SQL injection risk |
| `eval(`, `exec(`, `subprocess.call(shell=True` | HIGH | Code execution risk |
| Raw user input inserted into HTML/template without escaping | HIGH | XSS risk |
| New route/endpoint defined without auth middleware reference | HIGH | Missing authentication |
| New webhook endpoint without rate limit reference | MEDIUM | Missing rate limiting |
| `.env` file in changed files list | CRITICAL | Env file potentially committed |

For any CRITICAL security finding, the verdict is automatically BLOCKED regardless of other findings.

#### Pass F — Code Quality & Testability

For each new source file in CHANGED_FILES (added, not modified):
1. Check if a corresponding test file exists in the change set
   - Python: `test_<filename>.py` or `<filename>_test.py`
   - TypeScript: `<filename>.test.ts` or `<filename>.spec.ts`
2. If no test file is present AND the file is a service/handler/model: Finding Q-n, **HIGH**

Scan changed lines for:
- `# TODO`, `# FIXME`, `# HACK`, `// TODO`, `// FIXME` comments → **LOW**
- Functions/methods exceeding 60 lines (heuristic: count `def `/`function ` occurrences per file; flag files where average exceeds 60) → **MEDIUM**
- `print(` statements in non-test production code (should use logger) → **LOW**

---

### Phase 5: Severity Elevation (Strict Mode)

If `strict_mode = true`:
- Elevate all MEDIUM findings to HIGH
- Note in report header: "⚠️ Strict mode active: MEDIUM findings elevated to HIGH"

---

### Phase 6: Verdict Computation

Apply verdict rules in priority order:

```
IF any finding.severity == "CRITICAL"    → verdict = "BLOCKED"
ELSE IF any finding.severity == "HIGH"   → verdict = "CHANGES_REQUIRED"
ELSE IF any finding exists               → verdict = "APPROVED_WITH_WARNINGS"
ELSE                                     → verdict = "APPROVED"
```

The verdict is computed mechanically from the findings list. It is never modified by LLM judgment or user instruction.

---

### Phase 7: Report Output

Emit the complete Markdown review report to stdout. **Never write this report to disk.**

Use this exact structure:

```markdown
# Code Review Report — sp.review

**Feature**: <feature-slug>
**Date**: <YYYY-MM-DD>
**Branch**: <current-branch>
**Diff Base**: <diff_base>
**Mode**: <STANDARD | STRICT>
**Passes Run**: <all | specific-pass>

---

## Verdict

```
╔══════════════════════════════════════════╗
║  VERDICT: <VERDICT>                      ║
║                                          ║
║  <N> CRITICAL  <N> HIGH  <N> MEDIUM  <N> LOW  ║
╚══════════════════════════════════════════╝
```

---

## Findings

| ID | Category | Severity | Location | Summary | Recommendation |
|----|----------|----------|----------|---------|----------------|
<one row per finding, sorted: CRITICAL → HIGH → MEDIUM → LOW>

(If zero findings: "✅ No findings detected.")

---

## Coverage Summary

| Metric | Value |
|--------|-------|
| Requirements covered | N / T (%) |
| Tasks addressed in diff | N / T (%) |
| Constitution principles clean | N / 6 |
| Files changed | N |
| Lines added / removed | N / N |

---

## Next Actions

<If BLOCKED or CHANGES_REQUIRED:>
The following MUST be resolved before this can be merged:

N. **[ID]** <One-line fix description>
   → <Specific file:line or command>

After resolving all HIGH/CRITICAL findings, re-run: `/sp.review <feature-slug>`
When approved, proceed with: `/sp.git.commit_pr`

<If APPROVED_WITH_WARNINGS:>
Warnings noted but implementation may proceed. Consider addressing:
...

<If APPROVED:>
✅ All checks passed. Proceed with: `/sp.git.commit_pr`
```

---

### Phase 8: PHR Creation

After the report is emitted, create a Prompt History Record.

Determine stage:
- If verdict is `APPROVED` or `APPROVED_WITH_WARNINGS` → stage = `green`
- If verdict is `CHANGES_REQUIRED` or `BLOCKED` → stage = `red`

**PHR Creation Process (agent-native fallback):**

1. Run: `.specify/scripts/bash/create-phr.sh --title "spec-driven-code-review" --stage <stage> --feature <feature-slug> --json`

2. If the script fails or is unavailable:
   - Read `.specify/templates/phr-template.prompt.md`
   - Allocate next available ID in `history/prompts/<feature-slug>/`
   - Write file at: `history/prompts/<feature-slug>/<ID>-spec-driven-code-review.<stage>.prompt.md`
   - Fill ALL placeholders:
     - `{{ID}}` → allocated integer ID
     - `{{TITLE}}` → "Spec-Driven Code Review"
     - `{{STAGE}}` → determined stage
     - `{{DATE_ISO}}` → today YYYY-MM-DD
     - `{{SURFACE}}` → "agent"
     - `{{MODEL}}` → "claude-sonnet-4-6"
     - `{{FEATURE}}` → feature-slug
     - `{{BRANCH}}` → current git branch
     - `{{USER}}` → git config user.name or "unknown"
     - `{{COMMAND}}` → "/sp.review"
     - `{{LABELS}}` → `["code-review","spec-driven","quality-gate"]`
     - `{{LINKS_SPEC}}` → path to spec.md
     - `{{LINKS_TICKET}}` → "null"
     - `{{LINKS_ADR}}` → "null"
     - `{{LINKS_PR}}` → "null"
     - `{{FILES_YAML}}` → list of CHANGED_FILES (read-only, not modified)
     - `{{TESTS_YAML}}` → " - none"
     - `{{PROMPT_TEXT}}` → full $ARGUMENTS verbatim
     - `{{RESPONSE_TEXT}}` → "Review verdict: <VERDICT>. <N> findings: <N> CRITICAL, <N> HIGH, <N> MEDIUM, <N> LOW."
     - `{{OUTCOME_IMPACT}}` → verdict and top finding summary
     - `{{TESTS_SUMMARY}}` → "none (read-only review)"
     - `{{FILES_SUMMARY}}` → "<N> files reviewed; 0 files modified"
     - `{{NEXT_PROMPTS}}` → next action command
     - `{{REFLECTION_NOTE}}` → key insight from findings (or "No issues found" if APPROVED)
     - `{{FAILURE_MODES}}` → any E-D* warnings encountered
     - `{{GRADER_RESULTS}}` → "Verdict computed deterministically from findings"
     - `{{PROMPT_VARIANT_ID}}` → "sp.review-v1.0"
     - `{{NEXT_EXPERIMENT}}` → "none"

3. Validate no unresolved `{{PLACEHOLDERS}}` remain.

4. Report: `📝 PHR-<ID> recorded at history/prompts/<feature-slug>/<filename>`

---

## Error Reference

| Code | Trigger | Message | Action |
|------|---------|---------|--------|
| E-U1 | Missing SDD artifact | "tasks.md not found. Run /sp.tasks first." | Abort |
| E-U2 | Not in git repo | "Not inside a git repository." | Abort |
| E-U3 | Feature slug not found | "No feature dir for '<slug>'. Run /sp.specify first." | Abort |
| E-U4 | Invalid --diff-base ref | "Git ref '<ref>' is invalid." | Abort |
| E-S1 | git binary missing | "git is not installed or not in PATH." | Abort |
| E-S2 | Prerequisites script fails | "Prerequisite check failed: <error>." | Abort |
| E-S3 | File read fails | "Could not read <file>. Skipping." | Warn, continue |
| E-D1 | constitution.md missing | "Constitution not found. Pass A skipped." | Warn, continue |
| E-D2 | Empty git diff | "No code changes detected. Running artifact checks only." | Warn, continue |
| E-D3 | >50 findings generated | "<N> findings suppressed (50-finding cap reached)." | Log, continue |

---

## Operating Principles

### Read-Only Guarantee
- **NEVER modify** any source file, spec artifact, tasks.md, or constitution
- **NEVER create** commits, branches, or PRs
- **NEVER execute** code found in the diff

### Determinism
- Finding IDs are generated by category prefix + sequential integer: C1, C2, R1, T1, A1, S1, Q1
- Verdict is computed purely from the findings list — never from LLM judgment alone
- Re-running without changes MUST produce identical IDs, categories, and counts

### Report Hallucination Prevention
- NEVER fabricate file paths not present in the git diff output
- NEVER cite line numbers without reading the actual file content
- NEVER create findings for code patterns not observed in the diff
- If uncertain about a pattern, flag as LOW with explicit uncertainty note: "Possible <pattern>—verify manually"

### Refusal Policy
- If asked to auto-fix findings: "Review is read-only. Use /sp.implement to address findings."
- If asked to override verdict: "Verdict is computed from findings. Resolve CRITICAL/HIGH issues first."
- If asked to skip constitution checks: "Constitution checks are required per project governance."

---

## Integration in SDD Workflow

```
/sp.specify  →  /sp.clarify  →  /sp.plan  →  /sp.tasks  →  /sp.checklist
                                                                    ↓
                                                             /sp.analyze
                                                                    ↓
                                                             /sp.implement
                                                                    ↓
                                                             /sp.review   ← YOU ARE HERE
                                                                    ↓
                                                (APPROVED) /sp.git.commit_pr
```

---

As the main request completes, you MUST create and complete a PHR (Prompt History Record) using agent-native tools when possible (see Phase 8 above for full PHR instructions).

1) Determine Stage
   - APPROVED or APPROVED_WITH_WARNINGS → `green`
   - CHANGES_REQUIRED or BLOCKED → `red`

2) Generate Title and Determine Routing:
   - Title: "Spec-Driven Code Review" (slug: `spec-driven-code-review`)
   - Route: `history/prompts/<feature-name>/` (feature stage)

3) Create and Fill PHR (Shell first; fallback agent-native)
   - Run: `.specify/scripts/bash/create-phr.sh --title "spec-driven-code-review" --stage <stage> --feature <name> --json`
   - Open the file and fill remaining placeholders (YAML + body), embedding full PROMPT_TEXT (verbatim) and RESPONSE_TEXT (verdict + findings summary).
   - If the script fails: use agent-native tools per Phase 8 above.

4) Validate + report
   - No unresolved placeholders; path under `history/prompts/` and matches stage; stage/title/date coherent.
   - Print: ID + path + stage + title.
   - On failure: warn, don't block.
