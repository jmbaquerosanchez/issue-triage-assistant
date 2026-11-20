> Snapshot of 2026-11-20 for [Whether issue text and derived data can be redistributed](https://github.com/jmbaquerosanchez/issue-triage-assistant/issues/5). Not updated: later research supersedes it.

# Redistribution of issue text and derived data

Research for ticket #5 of the phase-1 map (#2). The question: can this repository publish a target repository's issue text, comments and documentation, or data derived from them (embeddings, a ready-built index), so that the demo runs without downloading anything?

This is not legal advice. It reports what the primary texts say, where they are ambiguous, and what comparable projects do. The demo mode is decided in #15. All sources were read on 2026-11-20; GitHub's Terms of Service quoted here are the version effective April 27, 2026.

## Short answer

- **GitHub's terms grant no right to redistribute other people's issues and comments outside GitHub.** The only license users grant each other is to use, display and reproduce content "through the Service". Since April 2026 the Terms also say they "do not restrict lawful access to or use of the contents of public repositories by third parties". So GitHub's terms are mostly not the obstacle. The obstacles are each author's copyright in their text and the privacy rules on personal data (usernames).
- **The API terms (Section H of the Terms of Service) say nothing about storing or redistributing.** They limit abuse, token sharing and spam, and send everything else to the rest of the Terms and the Privacy Statement.
- **Whether the repository's license covers issue text is the central ambiguity.** The Terms apply the repository's license to Content added "to a repository containing notice of a license" without defining whether issues are part of the repository. The MIT text covers "software and associated documentation files". Apache-2.0 names "issue tracking systems", but only for work "intentionally submitted ... for inclusion in the Work". Documentation that lives in the repository is a different case: the repository license covers it like any other file.
- **Derived data gets no category of its own** in GitHub's terms. Whether copyright reaches it depends on how much of the text it carries. A search index for hybrid search contains the text. Embeddings are not the text, but research shows they can be inverted to recover much of it.
- **Existing public datasets of GitHub issues do not rest on any grant from GitHub or from the issue authors.** They rely on the repositories' licenses (SWE-bench), put their own license on the whole dataset (GitBugs, GHTorrent), gate access behind terms and honor removal requests (The Stack), or say nothing (NLBSE'24, `lewtun/github-issues`, GH Archive). Most mask or drop personal data.

## 1. What GitHub's terms say about storing and redistributing content obtained through the API

### There is no separate API license

GitHub's API terms are Section H of its Terms of Service, which the summary table describes as "the rules for using GitHub's APIs, whether you are using the API for development or data collection" ([ToS, Summary](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#summary)). Its operative clauses:

> Abuse or excessively frequent requests to GitHub via the API may result in the temporary or permanent suspension of your Account's access to the API. [...]
>
> You may not share API tokens to exceed GitHub's rate limitations.
>
> You may not use the API to download data or Content from GitHub for spamming purposes, including for the purposes of selling GitHub users' personal information, such as to recruiters, headhunters, and job boards.
>
> All use of the GitHub API is subject to these Terms of Service and the [GitHub Privacy Statement](https://github.com/site/privacy).
>
> GitHub may offer subscription-based access to our API for those Users who require high-throughput access or access that would result in resale of GitHub's Service.

— [ToS § H, API Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#h-api-terms)

Nothing in § H forbids storing or redistributing API responses as such. The questions it leaves open go to the rest of the Agreement. That includes the Acceptable Use Policies: "You agree that you will not under any circumstances violate our Acceptable Use Policies" ([ToS § C](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#c-acceptable-use)).

### Information usage restrictions (AUP § 7)

> You may use information from our Service for the following reasons, regardless of whether the information was scraped, collected through our API, or obtained otherwise:
>
> * Researchers may use public, non-personal information from the Service for research purposes, only if any publications resulting from that research are open access.
> * Archivists may use public information from the Service for archival purposes.
>
> [...]
>
> You may not use information from the Service (whether scraped, collected through our API, or obtained otherwise) for spamming purposes, including for the purposes of sending unsolicited emails to users or selling personal information, such as to recruiters, headhunters, and job boards.
>
> Your use of information from the Service must comply with the GitHub Privacy Statement.

— [Acceptable Use Policies § 7](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies#7-information-usage-restrictions)

**Ambiguity:** the text does not say whether the two listed purposes are the *only* permitted uses, which would make the list a whitelist, or examples of permitted uses. Read as a whitelist, a public demo index that is neither research nor archiving would sit outside it. Read as examples, the only firm prohibitions are spam and selling personal data. The research purpose also requires "non-personal" information. Issue data always carries the authors' usernames.

### Services usage limits (AUP § 6)

> You will not reproduce, duplicate, copy, sell, resell or exploit any portion of the Service, use of the Service, or access to the Service without our express written permission.

— [AUP § 6](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies#6-services-usage-limits)

**Ambiguity:** the Terms define "Service" as "the applications, software, products, and services provided by GitHub". They define "Content" separately as "code, text, data, documentation [...] made available through the Service" ([ToS § A](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#a-definitions)). On that reading, copying users' issue text is not copying "a portion of the Service", but the text does not settle it.

### Privacy (AUP § 8)

> Any person, entity, or service collecting data from the Service must comply with the GitHub Privacy Statement, particularly in regards to the collection of personal information. If you collect any personal information from the Service, you agree that you will only use that personal information for the purpose for which that User has authorized it. You agree that you will reasonably secure any personal information you have gathered from the Service, and you will respond promptly to complaints, removal requests, and "do not contact" requests from us or other users.

— [AUP § 8](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies#8-privacy)

The issues API returns each author's login and the logins of everyone in the timeline. Comment bodies can also contain names, emails or @mentions. Publishing a snapshot therefore brings in the duty to honor removal requests.

### Public repositories and lawful access (ToS § D.8, new in April 2026)

> By choosing to contribute Content to a public repository, you are choosing to and directing us to make such Content accessible to everyone on the internet. Unless specifically set forth herein, these Terms do not restrict lawful access to or use of the contents of public repositories by third parties, or by GitHub or its Affiliates.

— [ToS § D.8](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#8-public-repositories-and-lawful-access)

This clause says the Terms themselves do not restrict third-party use. It grants no copyright license, though: "lawful" use still depends on copyright law and any license the author gave. "Unless specifically set forth herein" keeps the restrictions the Agreement does set, such as AUP §§ 7–8, since the Agreement includes "all other operating rules, policies [...] and procedures" ([ToS § A](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#a-definitions)).

### Access reciprocity (ToS § D.9)

§ D.9 applies to anyone who uses automated means to collect public Content "for the purpose of developing or training any commercially available artificial intelligence model". Such a party waives its own terms against GitHub doing the same. It "does not apply to Access solely for the purpose of academic research" or to parties with fewer than 700 million monthly active users ([ToS § D.9](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#9-access-reciprocity)). It sets no limit on redistribution and does not reach this project.

### What changed in April 2026

The April 27, 2026 revision ([github/docs@301baf1](https://github.com/github/docs/commit/301baf10d6e9c8f89460eea6b9ad577b2de6fdb9)) added § D.8 and reworded § D.5. The earlier version (effective November 16, 2020) granted other users a license "to reproduce Your Content solely on GitHub as permitted through GitHub's functionality (for example, through forking)" ([previous text](https://github.com/github/docs/blob/836fb8f1a60d620e10a8f2a1311e3c2eb24ba06a/content/site-policy/github-terms/github-terms-of-service.md)). The current text says "through the Service as permitted by GitHub's functionality". Neither version grants reproduction outside GitHub.

## 2. Who owns the text of issues and comments, and what the repository's license covers

### The author owns it

> You own Your Content. If you post Content you did not create, you are responsible for ensuring you have the right to post it and for complying with any applicable licenses.

— [ToS § D.3](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#3-ownership-and-license-grants)

"User-Generated Content" means "Content that you or other users upload, submit, or create through the Service" ([ToS § A](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#a-definitions)). Each issue and each comment belongs to whoever wrote it, not to the repository's owner. A target repository's history therefore has as many rights holders as it has distinct authors.

### The license users grant each other is limited to GitHub

> Your Content that you post publicly, including issues, comments, and contributions to other Users' repositories, may be viewed by others. [...]
>
> By making a repository public, you grant other Users a nonexclusive, worldwide license to use, display, perform and reproduce (by forking) Your Content through the Service as permitted by GitHub's functionality. You may grant additional rights by adopting a license.

— [ToS § D.5](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#5-license-grant-to-other-users)

The Terms name issues and comments explicitly, but only to say they "may be viewed by others". The reproduction license is tied to "making a repository public" and limited to "through the Service". Someone who comments on another person's repository makes no repository public, so the text does not clearly have them grant even that license. The ToS licenses also "end when you remove Your Content, unless other Users have forked it" ([§ D.3](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#3-ownership-and-license-grants)).

### Does the repository's license reach issues? Ambiguous

> Whenever you add Content to a repository containing notice of a license, you license that Content under the same terms, and you agree that you have the right to license that Content under those terms. If you have a separate agreement to license that Content under different terms, such as a contributor license agreement, that agreement will supersede.

— [ToS § D.6](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#6-contributions-under-repository-license)

The Terms do not define "repository". GitHub's docs describe one in terms that point both ways: "A repository contains all of your code, your files, and each file's revision history. You can discuss and manage your work within the repository." ([About repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories)). The section's own gloss ("inbound=outbound") is the open-source norm for code contributions.

The license texts most target repositories use draw their own boundaries:

- **MIT** grants rights over "this software and associated documentation files (the "Software")" ([SPDX: MIT](https://spdx.org/licenses/MIT.html)). Issue threads are not files in the repository.
- **Apache-2.0** defines a "Contribution" as work "intentionally submitted to Licensor for inclusion in the Work". It counts as "submitted" any communication "on electronic mailing lists, source code control systems, and issue tracking systems that are managed by, or on behalf of, the Licensor for the purpose of discussing and improving the Work" ([Apache License 2.0, § 1](https://www.apache.org/licenses/LICENSE-2.0)). So it does contemplate issue trackers, but only for material submitted *for inclusion in the Work*. A bug report or a "+1" comment is usually not that.

Without a license, GitHub's own docs state the default: "you retain all rights to your source code and no one may reproduce, distribute, or create derivative works from your work" ([Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)).

For contrast, when GitHub wants user contributions to be freely redistributable it says so expressly. Contributors to the Advisory Database "agree to release your contributions to the GitHub Advisory Database under the Creative Commons Zero license" ([Additional Product Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features)). Issues and comments have no equivalent clause.

### Documentation is a separate case

Documentation stored as files in the target repository is covered by the repository's license like any other file. MIT names "documentation files" explicitly. Redistributing it is allowed on the license's terms, for example by keeping the copyright and permission notice. Documentation published from a separate repository or site may carry a different license, such as a Creative Commons one. Which case applies depends on the target repository.

## 3. Is derived data treated differently?

**In GitHub's terms, no.** No clause distinguishes derived data. AUP § 7 covers "information from the Service [...] obtained otherwise", which would include information processed after collection. AUP § 8 follows personal information into whatever form it is stored in.

**In copyright, it depends on what the derived artifact carries.** No primary legal text found classifies embeddings or search indexes as such. The facts that bear on the question:

- **A search index carries the text.** A full-text index stores the terms and their positions. Search results that show snippets, titles or bodies need the original text stored alongside, and so do duplicate candidates in a demo. A "ready-built index" for hybrid search is, in practice, a copy of the corpus plus vectors.
- **Embeddings are lossy but invertible to a large degree.** Morris et al. report that an iterative method "is able to recover 92% of 32-token text inputs exactly" from embeddings of the encoder they studied ([Text Embeddings Reveal (Almost) As Much As Text, EMNLP 2023](https://arxiv.org/abs/2310.06816)). Embeddings alone are not obviously "non-text".
- **Facts and metadata are thinner material.** Examples are issue numbers, dates, labels, open/closed state and "issue A is a duplicate of issue B" links. Copyright protects expression, and these carry little or none. Logins remain personal data under AUP § 8.
- **The EU text-and-data-mining exceptions do not cover making copies available.** Directive (EU) 2019/790 permits "reproductions and extractions" for text and data mining. These "may be retained for as long as is necessary for the purposes of text and data mining" (Art. 4(1)–(2)), subject to the rights holder not having "expressly reserved" the use (Art. 4(3)). Art. 3 lets research organisations keep copies "for the purposes of scientific research". Both exceptions cover only "reproductions and extractions". Neither lists the right of communication to the public (Art. 3 of Directive 2001/29/EC) among the rights it makes an exception to ([Directive (EU) 2019/790](https://eur-lex.europa.eu/eli/dir/2019/790/oj)). So mining a corpus locally is within the exception, but publishing the corpus or an index that contains it is not.
- **US fair use exists but is decided case by case.** GitHub's Terms themselves point to it: "you must consider legal uses such as fair use and licensed uses" ([ToS § F](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#f-copyright-infringement-and-dmca-policy)). No source found addresses a demo index of issue text specifically.

## 4. What existing public datasets of GitHub issues do

| Dataset | What it publishes | Terms it publishes under | Personal data |
|---|---|---|---|
| [GH Archive](https://www.gharchive.org/) | Hourly archives of the public GitHub event stream ("JSON encoded events as reported by the GitHub API"), including issue and comment events; also a public BigQuery dataset. | No license or terms of use for the data. The code is MIT, and the website content is CC-BY-4.0 ([README](https://github.com/igrigorik/gharchive.org)). | Not addressed. |
| [GHTorrent](https://github.com/ghtorrent/ghtorrent.org/blob/master/faq.md) | Mirror of GitHub API data, including issues and comments (discontinued). | "For non-commercial uses [...] the dataset is distributed under the CC-BY-SA license"; commercial use by contacting the maintainer. | Stopped distributing emails and real names by default in March 2016. Access on request ended because of GDPR: "until GHTorrent's legal status is cleared, we cannot distribute this data anymore" ([pers-data](https://github.com/ghtorrent/ghtorrent.org/blob/master/pers-data.md)). |
| [The Stack: GitHub issues](https://huggingface.co/datasets/bigcode/the-stack-github-issues) (BigCode) | Issue and PR conversations with text and usernames (54 GB, 30.9M files per its card). | Gated: users accept The Stack's Terms of Use and share their contact details. Use "must abide by the terms of the original licenses". Anyone re-hosting must pass the terms on. | Emails, IPs and keys masked. Authors replaced with `username_{i}` in the text field, "intended for model training to avoid memorizing usernames". "Regularly updated to enact validated data removal requests". |
| [SWE-bench](https://huggingface.co/datasets/SWE-bench/SWE-bench) | 2,294 issue–PR pairs from 12 Python repositories, with the issue text as `problem_statement`. | No license on the dataset card; the code repository is MIT. The paper's ethics statement says the data comes "entirely from public repositories with licenses that permit software usage" and lists each repository's license ([arXiv 2310.06770](https://arxiv.org/abs/2310.06770)). | "we do not collect information about GitHub users". |
| [NLBSE'24 issue report classification](https://github.com/nlbse2024/issue-report-classification) | About 3,000 labelled issue reports from 5 projects, committed as CSV files in the repository. | The `LICENSE` file is empty. The README asks users to cite the work. | Not addressed. |
| [GitBugs](https://github.com/av9ash/gitbugs) | Bug reports for duplicate detection, including about 32,800 VS Code GitHub issues committed to the repository. | "released under the Creative Commons Attribution 4.0 International (CC BY 4.0) license", applied to the whole project with no mention of the original authors' rights. | Not addressed. |
| [IssueDupes](https://huggingface.co/datasets/primordic/IssueDupes) | Over 750K duplicate issue pairs from 25,000 repositories. | Gated and "currently invite only, intended for research and enterprise uses"; no license stated. | Not addressed. |
| [`lewtun/github-issues`](https://huggingface.co/datasets/lewtun/github-issues) (Hugging Face course) | Issues and comments of the `huggingface/datasets` repository, the publisher's own organization, built in the course's [chapter 5](https://github.com/huggingface/course/blob/main/chapters/en/chapter5/5.mdx) for a semantic-search exercise. | No license: the card's licensing section is an unfilled template. | Not addressed. |
| [github-to-sqlite demo](https://github.com/dogsheep/github-to-sqlite#demo) (not a dataset, but a public demo of issue data) | Issues, comments and more from the tool author's own repositories, served as a public Datasette database. | The database is not committed to the repository. A [CI workflow](https://github.com/dogsheep/github-to-sqlite/blob/main/.github/workflows/deploy-demo.yml) builds it with a token and deploys it. | The workflow blanks commit email addresses before publishing. |

Patterns:

- None of them cites a license or permission from GitHub or from the individual issue authors.
- They fall into four approaches: rely on the repositories' licenses (SWE-bench), put a blanket license on the derived dataset (GitBugs, GHTorrent), gate behind terms plus a removal process (The Stack, IssueDupes), or stay silent (NLBSE'24, `lewtun/github-issues`, GH Archive).
- The ones that handle personal data mask usernames and emails, or drop personal fields, and honor removal requests. GHTorrent stopped distributing personal data because of GDPR.
- The two demo-like cases (`lewtun/github-issues`, github-to-sqlite) use repositories that belong to the publisher's own organization.

## 5. Fallbacks if the text is not redistributed

These are the options found, with the facts that bear on each. The choice belongs to #15.

1. **Download script, nothing shipped.** The demo ingests the target repository on first run. Fact: unauthenticated REST requests are limited to "60 requests per hour", authenticated ones to 5,000 ([Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)). The per-issue timeline endpoint takes one request per issue. The repository-wide list endpoints for issues, comments and issue events return at most 100 items per page. Either way, a repository with a few thousand issues needs far more than 60 requests, so it needs a GitHub token or hours of waiting. A token conflicts with "one command and no API key" if that phrase covers GitHub tokens and not only model API keys: #15 needs to say which. GH Archive needs no token, but it holds the whole GitHub event stream, so one repository means downloading and filtering large hourly files or querying BigQuery with a Google account. It also records only what the Events API emitted, which "may be updated by GitHub at any point".
2. **Download script plus a small committed sample.** A sample is still redistribution: a smaller sample means less exposure, not a different legal category. Sample sources with clearer rights:
   - issues from a repository whose authors are the maintainer, such as this project's own tracker, where the rights holder can license the text;
   - synthetic issues written for the demo;
   - a target repository whose contributor terms explicitly license issue content, if one is found.
3. **Ship only facts, fetch the text at runtime.** Commit issue numbers, dates, labels and the duplicate-link ground truth, without bodies or logins, and download the text when the demo runs. The download problem of option 1 remains.
4. **Build the index in CI and host it outside git**, as a release asset or an external dataset, like the github-to-sqlite demo. Legally this is the same redistribution as committing it. The operational difference is removal: deleting an asset is immediate. Removing data from git history requires rewriting it, and the commits "may still be accessible" in clones, forks and "cached views on GitHub" ([Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)). That matters for the duty to "respond promptly to [...] removal requests" (AUP § 8).
5. **Mitigations that combine with any option:** pseudonymize authors as The Stack does, drop logins and emails, attach the target repository's license notice, and publish a removal-request path.

## 6. Open ambiguities

- **Whether ToS § D.6 makes a repository's license apply to issues and comments.** "Repository" is undefined. SWE-bench's practice assumes it does, but no GitHub text confirms it.
- **Whether AUP § 7 lists the only permitted uses or gives examples.** If it is a whitelist, a public demo that is neither research nor archiving would need GitHub's permission.
- **Whether the issue text counts as "any portion of the Service" under AUP § 6.** The definitions suggest not, since Content and Service are defined apart.
- **How § D.8, new in April 2026, interacts with AUP §§ 6–7.** It says the Terms do not restrict lawful third-party use of public repository contents "unless specifically set forth herein", and the AUP is part of the Agreement.
- **Whether embeddings without the text count as a copy.** No legal text found addresses it. Research shows substantial recoverability.
- **Whether "no API key" in the demo requirement includes a GitHub token.** For #15.

## 7. To check on the target repository once it is chosen

- The `LICENSE` file, and whether it is MIT-style ("software and associated documentation files") or Apache-2.0 (which mentions issue trackers).
- Where the documentation lives and under which license.
- Any contributor license agreement or contributing guide that says how issue and comment content is licensed. Under § D.6 such an agreement "will supersede".
- Whether the maintainers have published any statement on reuse of their tracker's content.

## Sources

GitHub:

- [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service), effective April 27, 2026 ([source](https://github.com/github/docs/blob/main/content/site-policy/github-terms/github-terms-of-service.md); [previous version, effective November 16, 2020](https://github.com/github/docs/blob/836fb8f1a60d620e10a8f2a1311e3c2eb24ba06a/content/site-policy/github-terms/github-terms-of-service.md))
- [GitHub Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)
- [GitHub General Privacy Statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement)
- [GitHub Terms for Additional Products and Features](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features)
- [Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
- [About repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories)
- [Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [Removing sensitive data from a repository](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

Licenses and law:

- [MIT License (SPDX)](https://spdx.org/licenses/MIT.html)
- [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- [Directive (EU) 2019/790 on copyright in the Digital Single Market](https://eur-lex.europa.eu/eli/dir/2019/790/oj), Arts. 2–4

Research:

- [Morris et al., Text Embeddings Reveal (Almost) As Much As Text, EMNLP 2023](https://arxiv.org/abs/2310.06816)
- [Jimenez et al., SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)

Datasets: linked in the table in § 4.
