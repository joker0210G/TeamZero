# TeamZero Agent Workflow Instructions (Claude Code, Antigravity, Cursor)

You have access to the **TeamZero MCP Server** (58+ tools). Use these tools systematically throughout your software development workflow.

---

## 1. Onboarding & Exploration (Day 1)
When joining this repository or exploring new code:
1. **Never read whole files blindly.** Call `teamzero_inspect_outline(file_path)` to get a compact AST outline (<15 lines).
2. **Read targeted symbols:** Call `teamzero_read_symbol(file_path, symbol_name)` or `teamzero_read_compressed(file_path)` to conserve context window.
3. **Discover architecture & god nodes:**
   - Call `teamzero_get_god_nodes()` to find the highest-coupling modules.
   - Call `teamzero_get_surprising_connections()` to check cross-community risk.
   - Run `teamzero_archaeology_scan()` to baseline the repository.

---

## 2. Planning & Task Execution
1. **Find next work:** Call `teamzero_get_next_task()`.
2. **Break down complex work:** If task complexity is >= 6, call `teamzero_expand_task(task_id, subtasks)`.
3. **Estimate complexity:** Call `teamzero_auto_score_complexity(description, target_files)`.
4. **Clean up duplicates:** Call `teamzero_merge_duplicate_tasks()`.

---

## 3. Pre-Flight Verification & Anti-Hallucination
Before editing or committing any new code:
1. **Surface Assumptions:** Call `teamzero_surface_assumptions(brief)` to flag ambiguous requirements.
2. **Verify Reality:** Call `teamzero_verify_grounding(code)` to verify that all imports and symbols exist in the repository AST.
3. **Multi-Method Fact Checking:**
   - Call `teamzero_cove_verify(candidate_code)` (Chain-of-Verification).
   - Call `teamzero_ever_verify(candidate_code)` (Real-time atomic statement verification).
   - Call `teamzero_ensemble_verify(candidate_code)` for high-risk modules.

---

## 4. Testing, Red Teaming & Merge Gate (Invariant 03)
**Rule: "Done is computed, never asserted."** You cannot say a task is finished until the gauntlet mathematically proves it:
1. **Run Static Gauntlet:** Call `teamzero_run_gauntlet()` to execute pytest and generate an HMAC receipt.
2. **Run Dynamic Gauntlet:** Call `teamzero_run_dynamic_gauntlet()` for dynamic edge-case probes and memory profiling.
3. **Run AI Red Team Cracker:** Call `teamzero_ai_redteam()` to evaluate business-logic exploit resistance.
4. **Check Merge Authority:** Call `teamzero_check_merge(ref="HEAD")`. If all 4 gates pass, submit the candidate.

---

## 5. Tool Search
If you are unsure which tool to use, run:
```python
teamzero_search_tools(query="what you want to do")
```
This semantically ranks the top tools for your query.
