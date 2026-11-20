> Snapshot of 2026-11-20 for [Existing AI triage and duplicate detection tools](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/6). Not updated: later research supersedes it.

# Existing AI triage and duplicate detection tools

Research for ticket #6. Researched on 2026-11-20 against primary sources: each tool's own docs, repository, workflow files or announcement; GitHub's docs and changelog; and the papers themselves. Where a claim could not be checked against its owner, the text says so.

**Question.** Which tools already triage GitHub issues with AI or detect duplicate issues, GitHub's own features included? For each one: what it does, whether a human approves its actions, whether it publishes an evaluation, and whether it is open source. Plus any published duplicate-detection baselines or datasets worth comparing against.

## Summary

- **Nearly every product and bot publishes no accuracy numbers.** That covers GitHub's native duplicate detection, the GitHub-built AI actions, the dedupe workflows that Anthropic, OpenAI and Google run on their own CLI repositories, Dosu, CodeRabbit, Linear, Kilo and the long tail of open-source Actions. The few that do measure are research papers, Mozilla's bugbug (for its component classifier, not duplicates), and one recent open-source benchmark, [triage-bench](#triage-bench-2026).
- **Time-aware evaluation of duplicate retrieval has prior art.** Rakha et al. (TSE 2018) showed that evaluating on a short window inflates results by a median of 17–42% and proposed a "realistic evaluation" over all reports in the tracker. Zhang et al. (TOSEM 2023) built a chronological benchmark that includes two GitHub projects, VS Code and Kibana. triage-bench (October 2026) runs a time split with a per-query time mask and 95% bootstrap confidence intervals on microsoft/vscode and astral-sh/uv. It is the closest match to this project's planned eval.
- **Human control varies widely.** It ranges from suggestion-only (GitHub's issue form, CodeRabbit, Codex), to comment plus label (Gemini CLI), to a draft queue (Dosu Auto Draft), staged previews (GitHub Agentic Workflows), auto-close after a veto window (Claude Code), and auto-apply per property (Linear).
- **GitHub now ships the primitives itself.** Duplicate suggestions appear in the issue form (public preview, June 2026). Semantic and hybrid issue search reached general availability in April 2026, with a REST `search_type` parameter.
- **Published baselines and datasets:** BM25F/REP (Sun et al. 2011), Bugzilla FTS and VSCodeBot as measured by Zhang et al., difflib, BM25, `bge-small` embeddings, hybrid RRF, a cross-encoder rerank and an LLM judge (triage-bench). Datasets: TOSEM-DBRD (includes VS Code and Kibana, 2018–2020), GitBugs (CC BY 4.0, includes VS Code) and the older Bugzilla sets from Lazar et al. (2014).

## Comparison table

"Approval" means the human control over write actions. "Eval" means a published measurement of accuracy.

| Tool | Kind | What it does | Duplicate technique | Approval | Eval | Open source |
|---|---|---|---|---|---|---|
| GitHub duplicate detection | GitHub-native, public preview | Up to 3 possible duplicates inline in the issue form | Undisclosed; "based on meaning" | Non-blocking suggestion to the reporter | None | No |
| GitHub semantic/hybrid issue search | GitHub-native, GA | Search issues by meaning; REST `search_type` | Semantic (embeddings) or hybrid | n/a (read-only) | None | No |
| `github/ai-assessment-comment-labeler` | GitHub-built Action | Label-triggered LLM assessment; adds labels and comments | None | Runs on a maintainer-applied label; then acts | None | MIT |
| `pelikhan/action-genai-issue-dedup` | Action shown on GitHub's blog | Compares the new issue to N recent issues | Small LLM pairwise verdicts, large LLM validation | Comment (optional label) | None | MIT |
| GitHub Agentic Workflows issue triage | GitHub Next sample | Type, priority, `duplicate` / `needs-info` labels, triage comment | Agent searches issues | Writes only through declared "safe outputs"; optional staged mode | None | MIT |
| Claude Code repo `/dedupe` | Vendor workflow | Comments up to 3 duplicates, auto-closes after 3 days | 5 parallel search agents over GitHub search, then a filter agent | Auto-close unless the author reacts 👎 or comments | None (logs events to Statsig) | No (all rights reserved) |
| Codex repo issue deduplicator | Vendor workflow | Comments up to 5 potential duplicates | Codex reads the latest 1,000 issues as JSON; open-only fallback pass | Comment only | None | Apache-2.0 |
| Gemini CLI repo dedup | Vendor workflow | Comment plus `status/possible-duplicate` label | MCP `duplicates` tool over embeddings refreshed hourly, then Gemini filters | Comment + label; removing the label signals disagreement | None | Workflow Apache-2.0; backend source not found |
| Dosu | Commercial SaaS | Auto-label, dedupe, cited answers | Undisclosed | Mention, Auto Draft (review queue) or Auto Reply | None | No |
| CodeRabbit issue enrichment | Commercial, open beta | Duplicates, similar issues, related PRs, labels, assignees | Semantic similarity over vectorized issues and PRs | Comment; labels auto-applied if configured | None | No |
| Linear Triage Intelligence | Commercial (Linear, not GitHub) | Duplicates/related, team, project, assignee, labels | Semantic search for candidates, then an LLM classifies each | Accept/decline; per-property auto-apply | None | No |
| Kilo Auto-Triage | Commercial | Duplicates, 4-way classification with confidence, labels | Vector similarity vs previously triaged issues | No approval step described | None | Not stated |
| Long-tail Actions (several) | Open source | Duplicate comments, labels, sometimes closing | String distance, embeddings with threshold, or an LLM | Mostly comment; some close automatically | None | MIT |
| Mozilla bugbug | Open source (Mozilla) | Component, type, spam and other classifiers for Bugzilla | Duplicate model removed in 2023 | Auto-moves bugs above 60% confidence | Yes, for the component classifier (>80% precision on a later period) | MPL-2.0 |
| triage-bench | Open-source benchmark | Time-split eval of duplicates and labels | difflib, BM25, embeddings, hybrid, rerank, LLM judge | Phase 2 service in shadow mode | Yes (95% bootstrap CIs) | MIT |

## GitHub-native features

### Duplicate detection in the issue form (public preview, June 2026)

- Announced on 2026-06-18: "issue creation now flags potential matches against existing issues in the repository as issue details are being populated"; matches "appear inline in the issue creation form with up to three suggestions"; "available as a public preview" ([changelog](https://github.blog/changelog/2026-06-18-duplicate-detection-and-issue-fields-mcp-support-for-github-issues)).
- GitHub's docs: suggestions "appear once the title is filled out and the body reaches 100 characters", "up to three existing issues may be shown", and they "are non-blocking and do not prevent you from creating your issue" ([Creating an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-an-issue)).
- The announcement discussion adds the following. The title needs at least 20 characters. Title edits re-run the search, but later body edits do not. "Results are based on meaning, not just keyword matching". Confidence scores and a re-check button are "on our minds", and configurable thresholds are being explored ([community discussion #199395](https://github.com/orgs/community/discussions/199395)).
- No technique details, per-repository setting or accuracy figures are published in any of these.
- Precedent: a "Related issues" public beta in 2018 that "searches across all issues in your repository" while drafting ([changelog, 2018-11-05](https://github.blog/changelog/2018-11-05-related-issues/)).
- Copilot for Slack and Microsoft Teams "also checks for similar issues before creating a new one" ([changelog, 2026-09-25](https://github.blog/changelog/2026-09-25-updates-to-github-copilot-for-slack-and-microsoft-teams/)).

### Semantic and hybrid issue search (GA, April 2026)

- Search issues "by meaning, not just keywords". Natural-language queries combine meaning-based and exact keyword matching. It entered public preview in January 2026 and reached GA on 2026-04-02 ([changelog](https://github.blog/changelog/2026-04-02-improved-search-for-github-issues-is-now-generally-available/)).
- REST: `GET /search/issues` takes `search_type=semantic` ("a pure semantic (vector) search using embedding-based understanding") or `hybrid` ("combines semantic search with lexical search"). These modes require authentication and are "rate limited to 10 requests per minute". Some queries fall back to lexical search, with reasons such as `no_text_terms` and `quoted_text` ([REST docs](https://docs.github.com/en/rest/search/search#search-issues-and-pull-requests)). The docs do not say whether date qualifiers such as `created:<…` combine with semantic search. They also do not say whether the index reflects an issue's current text or its text at any past point.

### How duplicates are recorded (relevant to ground truth)

- A comment with "Duplicate of #N" creates a timeline event ("marked this as a duplicate of #97"), but only if the commenter has write access. Undo adds an unmark event ([docs](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/marking-issues-or-pull-requests-as-a-duplicate)).
- "Close as duplicate" exists since 2024-12-12, with a timeline event and a note ([changelog](https://github.blog/changelog/2024-12-12-github-issues-projects-close-issue-as-a-duplicate-rest-api-for-sub-issues-and-more/)). Closing as duplicate through the REST API exists since 2025-07-17 ([changelog](https://github.blog/changelog/2025-07-17-duplicate-issues-create-from-anywhere-and-more/)).

### GitHub-built AI triage Actions

- **AI assessment comment labeler** (`github/ai-assessment-comment-labeler`, MIT). GitHub's docs call it an "AI-powered issue intake tool" that judges whether an issue is actionable or needs more information, and adds comments or labels. By default it runs when the `request ai review` label is applied. The docs tell maintainers to "Review the suggestions provided by the tool and take appropriate action on the issue". The docs do not mention duplicate detection or any evaluation ([docs](https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/triaging-an-issue-with-ai); [changelog, 2025-09-05](https://github.blog/changelog/2025-09-05-github-actions-ai-labeler-and-moderator-with-the-github-models-inference-api)). Its companion `github/ai-moderator` (spam detection) is now archived. Both run on `actions/ai-inference` (MIT) and GitHub Models.
- **GitHub blog workflows for maintainers** (2025-08-28). The duplicate workflow uses `pelikhan/action-genai-issue-dedup`, with scope knobs `labels`, `count` and `since`. It "only comments"; the post recommends keeping "maintainers in the loop until you trust the automation" and gives no metrics ([GitHub blog](https://github.blog/open-source/maintainers/how-github-models-can-help-open-source-maintainers-focus-on-what-matters/)). The action's README describes the algorithm: optional label auto-classification, retrieval of `count` issues (default 30), batched pairwise `DUP`/`UNI` verdicts from a small LLM, then validation by a large LLM. It can optionally add a `duplicate` label (MIT; [repo](https://github.com/pelikhan/action-genai-issue-dedup)).
- **GitHub Agentic Workflows (gh-aw)**, from GitHub Next and Microsoft Research (`github/gh-aw`, MIT). The issue-triage sample sets the type and labels (type, priority, `needs-info`, `duplicate`) and posts a triage comment. Duplicate search covers open and recent closed issues and shows at most 3 matches. It insists: "Never mark an issue duplicate based only on similar words in the title". The agent has read-only permissions. Writes go through declared "safe outputs" with allowlists and caps, and labels "are applied automatically by this sample". The sample advises: "configure human review before enabling consequential routing or classification actions" ([gallery](https://github.github.com/gh-aw/gallery/ai-issue-triage/)). Safe outputs support `staged: true`, which "lets you preview what safe outputs a workflow would create without actually creating anything" ([safe outputs reference](https://github.github.com/gh-aw/reference/safe-outputs/)). No evaluation is published.

## Dedupe workflows run by AI vendors on their own repositories

These are the most visible LLM dedupe deployments on GitHub. Each is configured in the repository's `.github/workflows`.

- **anthropics/claude-code.** On every new issue, `claude-dedupe-issues.yml` runs `claude-code-action` with the `/dedupe` command ([workflow](https://github.com/anthropics/claude-code/blob/main/.github/workflows/claude-dedupe-issues.yml), [command](https://github.com/anthropics/claude-code/blob/main/.claude/commands/dedupe.md)). The steps are:
  - It skips issues that are closed, broad feedback, or already handled.
  - It summarizes the issue.
  - It launches "5 parallel agents to search Github for duplicates of this issue, using diverse keywords and search approaches".
  - A further agent filters out false positives.
  - It posts up to 3 candidates.

  The comment says the issue "will be automatically closed as a duplicate in 3 days" unless the author comments or reacts 👎 ([comment script](https://github.com/anthropics/claude-code/blob/main/scripts/comment-on-duplicates.sh)). `auto-close-duplicates.ts` then closes the issue with `state_reason: duplicate` if, after 3 days, there has been no later comment and no 👎 from the author ([script](https://github.com/anthropics/claude-code/blob/main/scripts/auto-close-duplicates.ts)). The workflow logs a `github_duplicate_comment_added` event to Statsig, and no accuracy figure is published. A separate `/triage-issue` command applies labels only, and it searches for duplicates among open issues. The repository's license reads "All rights reserved", so the source is visible but not open source ([LICENSE.md](https://github.com/anthropics/claude-code/blob/main/LICENSE.md)).
- **openai/codex.** `issue-deduplicator.yml` dumps the 1,000 most recent issues of any state to JSON, with bodies truncated to 4,000 characters, and asks Codex (read-only sandbox, JSON output schema) for up to 5 issues that "describe the same underlying problem". The prompt says "Return fewer matches rather than speculative ones". If that pass finds nothing, a fallback pass searches open issues only. The workflow comments "Potential duplicates detected. Please review them and close your issue if it is a duplicate." It does not close or label anything ([workflow](https://github.com/openai/codex/blob/main/.github/workflows/issue-deduplicator.yml); repo Apache-2.0). No evaluation is published.
- **google-gemini/gemini-cli.** `gemini-automated-issue-dedup.yml` runs Gemini CLI with one MCP tool, `duplicates`, served from a container image (`ghcr.io/google-gemini/gemini-cli-issue-triage`) backed by Firestore. Gemini then keeps only the candidates it is "highly confident are actual duplicates". The workflow posts a comment and adds `status/possible-duplicate`, and the comment says: "If you believe this is not a duplicate, please remove the `status/possible-duplicate` label" ([workflow](https://github.com/google-gemini/gemini-cli/blob/main/.github/workflows/gemini-automated-issue-dedup.yml)). An hourly workflow calls the tool's `refresh` to "refresh the embeddings for all open issues" ([workflow](https://github.com/google-gemini/gemini-cli/blob/main/.github/workflows/gemini-scheduled-issue-dedup.yml)). I found no public source for the MCP server image. Separately, `google-github-actions/run-gemini-cli` (Apache-2.0) ships real-time and scheduled issue-triage example workflows for labeling ([example](https://github.com/google-github-actions/run-gemini-cli/tree/main/examples/workflows/issue-triage)).

## Commercial products

- **Dosu.** Its blog (2025-04-15) says Dosu can "automatically apply relevant labels", "identify similar or duplicate issues", and "generate suggested responses that maintainers can review, edit, and approve before posting". No technique or metrics are given ([blog](https://dosu.dev/blog/automating-github-issue-triage)). The current docs define three reply modes ([Agent Reply Modes](https://app.dosu.dev/9affd04a-e6a9-452c-b927-c639e979994c/documents/2c956d56-d24a-4346-9023-87bf4d178ce0)):
  - **Mention:** Dosu responds only when mentioned. This is the default.
  - **Auto Draft:** Dosu "drafts a response on its own and queues it on the Review page instead of posting".
  - **Auto Reply:** Dosu posts on its own, subject to quality checks.

  The GitHub integration answers "tagged questions in issues and discussions" with citations ([GitHub integration](https://app.dosu.dev/9affd04a-e6a9-452c-b927-c639e979994c/documents/222de567-e12f-499d-a153-0b7a05c0faf4)). Dosu is a hosted service, and I found no source repository.
- **CodeRabbit issue enrichment** (open beta). On create or edit, it posts a comment with duplicate detection "using semantic similarity search over vectorized representations of issues and PRs", plus similar issues, related PRs and suggested assignees. Labels are applied automatically when `auto_apply_labels: true`. No metrics are given ([docs](https://docs.coderabbit.ai/issues/enrichment.md)).
- **Linear Triage Intelligence** (Linear's own tracker, included as the most detailed public write-up). A semantic search backend produces candidates, and LLMs classify each one "as a duplicate, loosely related, or unrelated". The first version used GPT-4o mini and Gemini 2.0 Flash; the current one uses GPT-5 and Gemini 2.5 Pro, with an agentic approach that pulls extra context ([how we built it, 2025-09-03](https://linear.app/blog/how-we-built-triage-intelligence)). Duplicates and related issues appear as relation suggestions to accept or dismiss. Teams, projects, assignees and labels can be shown, hidden or auto-applied per property ([docs](https://linear.app/docs/triage-intelligence); [auto-apply changelog](https://linear.app/changelog/2025-09-19-auto-apply-triage-suggestions)). An earlier "similar issues" feature (2023) used LLM embeddings, cosine similarity and pgvector, and also suggested duplicates at issue creation ([blog](https://linear.app/blog/using-ai-to-detect-similar-issues)). No offline evaluation or metrics appear in either post.
- **Kilo Auto-Triage.** It compares each new issue "against every previously-triaged issue in your repository using vector-similarity search". On a match it posts a comment with the original and a similarity score, and applies `kilo-triaged` and `kilo-duplicate`. It classifies issues as bug, feature, question or unclear, with a 0–1 confidence, and uses only labels that already exist in the repository. No approval step and no metrics are described ([docs](https://kilo.ai/docs/automate/auto-triage/overview)).

## Open-source bots and Actions

### Current long tail

All of these are MIT-licensed, have small user bases (0–25 stars as of 2026-11-20), and publish no evaluation. Their READMEs mention no precision, recall or benchmark.

- [`wow-actions/potential-duplicates`](https://github.com/wow-actions/potential-duplicates): Damerau–Levenshtein title similarity; threshold 0.6 by default; comments with a percentage.
- [`mackgorski/ai-duplicate-detector`](https://github.com/mackgorski/ai-duplicate-detector): OpenAI embeddings stored in SQLite; duplicate threshold 0.85 and related threshold 0.82. It labels duplicates, "closes them, and marks them as 'not planned'".
- [`MrcDprm/issue-triage-action`](https://github.com/MrcDprm/issue-triage-action): embedding similarity against the 100 most recently updated issues (cosine ≥ 0.75), then an LLM keeps "only the ones that report the same problem"; also labels issues and asks for missing details.
- [`ivosetyadi/issue-triage`](https://github.com/ivosetyadi/issue-triage): compares against open issues with token-level cosine, or with embeddings if a key is supplied; comments `possible-duplicate`.
- [`Shashank-8p/issue-detector`](https://github.com/Shashank-8p/issue-detector): OpenAI embeddings in Pinecone; "The final decision always remains with a human maintainer."
- [`zeldrisho/issue-triage-agent`](https://github.com/zeldrisho/issue-triage-agent): LLM triage with duplicate search (up to 5 open and 5 closed candidates) and context-aware replies.

### Earlier and historical

- **VS Code's `vscodebot`.** In 2018 it posted "(Experimental duplicate detection)" comments with candidate links and a hidden similarity score (for example `<!-- score: 0.541 -->`) ([example on microsoft/vscode#45977](https://github.com/microsoft/vscode/issues/45977)). Zhang et al. report that it recommends up to five candidates after submission, that its implementation "is not open-sourced", and that 11,808 of 62,092 VS Code bug reports received recommendations ([paper](https://ar5iv.labs.arxiv.org/html/2212.00548)). VS Code's triage Actions, including an ML classifier that generates assignees and labels from a monthly-trained model, are now archived ([repo](https://github.com/microsoft/vscode-github-triage-actions), MIT).
- **Mozilla bugbug** (MPL-2.0). This ML platform for Bugzilla has classifiers for component, type, spam, regression and more ([repo](https://github.com/mozilla/bugbug)).
  - The component classifier "automatically assigns a product and component", acting only above a 60% confidence threshold. Mozilla reported ">80% precision" on bugs triaged between December 2018 and March 2019, a period later than its training data. Training bugs were "rolled back" to their state at filing to avoid leakage ([Mozilla Hacks, 2019-04-09](https://hacks.mozilla.org/2019/04/teaching-machines-to-triage-firefox-bugs/)).
  - In code, `bug_snapshot.rollback` restores a bug to its state at creation or at a given time ([source](https://github.com/mozilla/bugbug/blob/master/bugbug/bug_snapshot.py)). `issue_snapshot.rollback` restores a GitHub issue's original title from `renamed` events ([source](https://github.com/mozilla/bugbug/blob/master/bugbug/issue_snapshot.py)).
  - bugbug had a duplicate model, removed on 2023-11-29 in a commit titled "Drop the duplicate model" (commit `cd088476`).
- **Issue Label Bot** (Kubeflow/GitHub, MIT, archived). It predicted bug, feature request or question, and "may not apply any label in circumstances where the prediction is uncertain". The bot "is no longer live" ([repo](https://github.com/machine-learning-apps/Issue-Label-Bot)).
- **Ticket Tagger** (AGPL-3.0). A fastText issue-type classifier published as a GitHub App, described in ICSME 2019 and SCP 2021 papers, and the baseline for the NLBSE'22 tool competition ([repo](https://github.com/rafaelkallis/ticket-tagger)).

## Research, benchmarks and datasets

### Evaluation methodology for duplicate retrieval

- **Rakha, Bezemer, Hassan, "Revisiting the Performance Evaluation of Automated Approaches for the Retrieval of Duplicate Issue Reports", IEEE TSE 44(12), 2018** ([doi:10.1109/TSE.2017.2755005](https://doi.org/10.1109/TSE.2017.2755005); [PDF](https://sailresearch.github.io/sail-website/data/pdfs/TSE2017_RevisitingThePerformanceEvaluationOfAutomatedApproachesForTheRetrievalOfDuplicateIssueReports.pdf)).
  - Prior work evaluated on "data that spans a relatively short period of time (i.e., the classical evaluation)", which ignores masters outside the window. The authors propose "a realistic evaluation using all the reports that are available in the ITS".
  - On Mozilla, Eclipse and OpenOffice, the classical evaluation "completely ignores up to 23.5% of the duplicates" and "relatively overestimates the performance of BM25F and REP ... by a median of 17-42%".
  - Limiting the search to the last n months "does not lead to a significant improvement" without hurting performance.
  - Using the resolution field as it stood "at the time of reporting the new duplicate issue" improves results by a median of 7–21.5%.
- **Rakha, Bezemer, Hassan, EMSE 23, 2018**: "Revisiting the performance of automated approaches for the retrieval of duplicate reports in issue tracking systems that perform just-in-time duplicate retrieval" ([doi:10.1007/s10664-017-9590-5](https://doi.org/10.1007/s10664-017-9590-5)). It studies trackers that suggest duplicates at filing time, which GitHub has done since June 2026. Its full text and abstract were not accessible to me, so I report only its subject.
- **Zhang, Han, Vinayakarao, Irsan, Xu, Thung, Lo, Jiang, "Duplicate Bug Report Detection: How Far Are We?", ACM TOSEM, 2023** ([arXiv:2212.00548](https://arxiv.org/abs/2212.00548); [HTML](https://ar5iv.labs.arxiv.org/html/2212.00548)).
  - **Benchmark:** recent data (2018-01-01 to 2020-12-31) from Bugzilla (Eclipse, Mozilla), Jira (Hadoop, Spark) and GitHub (Kibana with 17,016 reports and 470 duplicates; VS Code with 62,092 reports and 4,386 duplicates).
  - **Protocol:** a chronological split, two years for training and the last year for testing. Candidates are reports from within one year, and the metric is Recall Rate@k for k = 1–10.
  - **GitHub ground truth:** a regex over "Duplicate of #N"-style comments, manually checked at 99.2% (Kibana) and 94.5% (VS Code) precision. False negatives were not checked.
  - **Findings:** "the age of data significantly affects DBRD performance", and the tracker also matters. REP (BM25F-based) is best on most projects, though SABD beats it on VS Code by 9% in RR@10. REP beats VSCodeBot by 9.8% in RR@5. The best research tools beat Mozilla's full-text search by 22.1–62.7% in RR@10, while FTS beats the deep-learning tools HINDBR and DC-CNN.
  - **Positioning:** the authors argue ranking is more realistic than pairwise classification, because "the real scenario presents a much larger set of negative candidates".
  - **Replication package:** [soarsmu/TOSEM-DBRD](https://github.com/soarsmu/TOSEM-DBRD). It has no license file; the data is on a SharePoint link, and REP is run via [fast-dbrd](https://github.com/irving-muller/fast-dbrd-modified) with `--time-constraint 365`.

### Techniques and baselines

- **REP / BM25F:** Sun, Lo, Khoo, Jiang, "Towards More Accurate Retrieval of Duplicate Bug Reports", ASE 2011 ([doi:10.1109/ASE.2011.6100061](https://doi.org/10.1109/ASE.2011.6100061)). It is the long-standing strong baseline in both evaluation papers above.
- **CUPID:** Zhang, Irsan, Thung, Lo (arXiv 2023, rev. 2024) combines REP with ChatGPT. It reports RR@10 of 0.602–0.654 on three datasets and a 5–8% improvement over the prior state of the art ([arXiv:2308.10022](https://arxiv.org/abs/2308.10022)).
- **Embedding comparisons:** Patil, Han, Jadon compare TF-IDF, FastText, Gensim, BERT and ADA embeddings for retrieving similar bug reports. BERT gave the best recall ([arXiv:2308.09193](https://arxiv.org/abs/2308.09193)).

### Datasets

- **Lazar, Ritchey, Sharif, "Generating duplicate bug datasets", MSR 2014** ([doi:10.1145/2597073.2597128](https://doi.org/10.1145/2597073.2597128)): the classic Bugzilla duplicate datasets.
- **GitBugs** (Patil et al., arXiv 2025, rev. 2026): more than 150,000 reports from nine projects across GitHub, Bugzilla and Jira, with predefined train/test splits for duplicate detection ([arXiv:2504.09651](https://arxiv.org/abs/2504.09651)). The README lists VS Code at 32,829 reports and 9,238 duplicates, and the license is CC BY 4.0 ([repo](https://github.com/av9ash/gitbugs)). That VS Code duplicate rate (28%) differs from Zhang et al.'s 7% for 2018–2020. The page does not say how duplicates were labeled.
- **NLBSE tool competitions** on issue-type classification. NLBSE'23 has more than 1.4 million labeled GitHub issues (bug, enhancement, question, documentation) with FastText and RoBERTa baselines ([repo](https://github.com/nlbse2023/issue-report-classification)). NLBSE'24 has 3,000 issues from 5 projects with Sentence-Transformers baselines ([repo](https://github.com/nlbse2024/issue-report-classification)). These are relevant to classification (phase 2), not duplicates.
- **Hugging Face course:** semantic search over the 🤗 Datasets repository's issues (`lewtun/github-issues`) with `multi-qa-mpnet-base-dot-v1` and FAISS. It is a teaching example with no evaluation ([course](https://huggingface.co/learn/llm-course/chapter5/6)).

### triage-bench (2026)

[TiagoCK/triage-bench](https://github.com/TiagoCK/triage-bench) (MIT; created 2026-10-15) is "an open, time-split benchmark and evaluation harness for GitHub issue triage: label prediction and duplicate detection". Everything below comes from its README.

- **Leakage control:**
  - Issues created before a cutoff form the train set and search index; later issues are the test set.
  - A **per-query time mask** limits search to issues created before each duplicate, enforced by `tests/test_leakage.py`.
  - The label vocabulary comes from train issues only.
  - The search corpus reaches back further than the test window.
- **Ground truth:**
  - It comes from `MarkedAsDuplicateEvent` timeline events (cancelled by unmarking) and "Duplicate of #N" comments, including full URLs.
  - Direction is inferred, not trusted. On astral-sh/uv, the event's `canonical` field "was always the issue whose timeline it came from"; trusting it yielded 7 pairs, while the inference rules found 401.
  - It excludes labels that issue forms apply automatically. On huggingface/transformers, 1,608 of 1,619 `bug` labels came from the form.
  - It skips repositories with too little ground truth: fewer than 20 test duplicates, or fewer than 50 labeled test issues.
- **Systems and metrics:**
  - **Systems:** difflib, BM25, `bge-small-en-v1.5` embeddings, hybrid RRF, `bge-reranker-base`, and an LLM judge over the hybrid top 5 (Claude Haiku, local Qwen).
  - **Metrics:** Recall@1/5/10 and MRR@10; average precision and recall at 90% precision at the natural duplicate rate; and "P@base", the share of bot comments that would be correct at the real duplicate rate. Every metric comes with a 95% bootstrap CI.
- **Reported results:**
  - **Retrieval:** on vscode (11,198 test issues, 603 test duplicates), Recall@5 is 0.29 for difflib, 0.39 for BM25, 0.55 for embeddings and 0.53 for embeddings + BM25.
  - **Similarity scores:** they "can't separate duplicates from new issues", with average precision of 0.01–0.02.
  - **LLM judge:** it raises top-1 accuracy (0.23 → 0.35–0.39), but it flags non-duplicates at 0.17 (Haiku) to 0.48 (Qwen) on vscode. At the real duplicate rate, only about 10% of Haiku's duplicate comments would be correct.
  - **Confidence gates:** none reached 50% precision on validation.
  - **Undercounting:** recorded duplicates undercount correct calls, so these numbers are a lower bound.
  - **Labels:** a TF-IDF + logistic regression classifier matches or beats both LLMs.
- **Phase 2 (in progress):** a GitHub App service in **shadow mode** ("it records what it would do and never posts to GitHub"). It tracks outcomes, offers a `/review` page for human-checked precision, and has a replay mode that checks parity with the offline benchmark.

## Observations relevant to this project

These are facts and direct implications, not a positioning decision.

- **Who publishes measurements.** No commercial product, no GitHub-native feature and no vendor workflow found here publishes an accuracy figure for duplicate detection. Published measurements come from research (Rakha et al., Zhang et al., CUPID, GitBugs), bugbug's component classifier and triage-bench.
- **Time-aware replay is established practice in research.** It appears as Rakha's "realistic evaluation", Zhang's chronological split with a one-year candidate window, bugbug's rollback to filing state, and triage-bench's per-query time mask with CIs. Of these, triage-bench overlaps most with this project's phase-1 eval: GitHub issues, a cutoff, maintainer-recorded duplicates, CIs, and a CLI harness whose CI runs offline on a synthetic fixture.
- **Points the prior art handles differently or not at all.** Each one is a fact about the sources above.
  - triage-bench uses issues' final labels, "not the labels at open time", and computes BM25 IDF "over the whole window".
  - Zhang et al. restrict candidates to one year, while Rakha et al. argue against ignoring older masters.
  - None of the sources I read describes reconstructing an issue's title and body as they stood at the cutoff. bugbug's GitHub rollback restores only the original title, from `renamed` events.
  - GitHub's semantic and hybrid search API is a possible off-the-shelf baseline. Its docs do not say whether it can be queried as of a past date, and it is limited to 10 requests per minute.
- **Ground-truth caveats documented by others:**
  - "Duplicate of" needs write access to create a timeline event (GitHub docs).
  - Regex-based extraction misses some duplicates; Zhang et al. did not check false negatives.
  - `MarkedAsDuplicateEvent` direction is unreliable (triage-bench).
  - Maintainers link each duplicate to only one original, so correct alternative originals go unrecorded (triage-bench).
- **Duplicates suggested at filing time** (GitHub since June 2026, Bugzilla before it) change which duplicates get filed. This is the subject of Rakha et al. (EMSE 2018). For a target repository whose history crosses June 2026, issues filed before and after the preview may not be comparable. This is an implication of the sources, not a measured fact.
- **Approval models in use**, from least to most autonomous:
  - Suggestion to the reporter (GitHub issue form).
  - Comment only (Codex, CodeRabbit, the GitHub blog workflow).
  - Comment plus label, with a way to dissent (Gemini CLI).
  - Draft queue (Dosu Auto Draft).
  - Staged preview (gh-aw).
  - Auto-close after a veto window (Claude Code, `mackgorski/ai-duplicate-detector`).
  - Per-property auto-apply (Linear).
