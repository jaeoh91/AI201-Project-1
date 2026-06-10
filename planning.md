# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

**Domain:** Policies & Regulations relevant to international students on a F1 Visa (the most common student visa type) at Georgia Tech.



---

## Documents

All sources are from policy documents provided by the Georgia Institute of Technology's Office of International Education, International Student & Scholar Services. (Link: https://isss.oie.gatech.edu/ISSS_F_Current)

Wrote a simple python script (`download_sources.py`) to scrape each website, and download only the policy text (avoiding links, banners, and other elements on the website that could add junk data). 

Additionally, to aid with the recursive chunking strategy we implement later, we went beyond simply copying the website text (which in testing resulted in broken sentences and overall messy formatting that would be problematic for any chunking strategy). Instead, the script walks the HTML tree tag-by-tag and converts each element into structured plain text similar to markdown: headings (`<h1>`–`<h6>`) become `# Heading` lines surrounded by blank lines, paragraphs (`<p>`) are separated by double newlines, list items (`<ul>`/`<ol>`) are rendered as `- item` or `1. item` lines, and tables are flattened into pipe-separated rows. Navigation elements, banners, scripts, and footers are stripped entirely. 

The result is a document where every natural section boundary is marked by a `\n\n`, which is exactly the delimiter that `RecursiveCharacterTextSplitter` tries first — meaning the chunker will respect paragraph and heading structure before ever splitting mid-sentence.


| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Regulations Overview | Webpage | https://isss.oie.gatech.edu/node/4097 |
| 2 | F Immigration Document Overview | Webpage | https://isss.oie.gatech.edu/node/4098 |
| 3 | Enrollment Requirements | Webpage | https://isss.oie.gatech.edu/node/4100 |
| 4 | Understanding Your I-20/DS-2019 | Webpage | https://isss.oie.gatech.edu/understanding-your-i-20ds-2019 |
| 5 | I-20 Updates: Keeping your I-20 Up-To-Date | Webpage | https://isss.oie.gatech.edu/node/3431 |
| 6 | Digitally-signed I-20 Form Guidance | Webpage | https://isss.oie.gatech.edu/content/digitally-signed-i-20-form-guidance |
| 7 | Travel | Webpage | https://isss.oie.gatech.edu/node/4099 |
| 8 | Renewing Your Visa | Webpage | https://isss.oie.gatech.edu/node/2794 |
| 9 | Taxes for Non-Residents | Webpage | https://isss.oie.gatech.edu/node/181 |
| 10 | Change of Status to F-1 | Webpage | https://isss.oie.gatech.edu/content/change-visa-status-f-1 |
| 11 | Transfer SEVIS Record to Another U.S. Institution | Webpage | https://isss.oie.gatech.edu/node/4095 |
| 12 | Change of Status From F-1 | Webpage | https://isss.oie.gatech.edu/node/4096 |
| 13 | Out of Status Options | Webpage | https://isss.oie.gatech.edu/node/3967 |
| 14 | Social Security Numbers | Webpage | https://isss.oie.gatech.edu/node/3399 |
| 15 | F-1 Employment Overview | Webpage | https://isss.oie.gatech.edu/node/3143 |
| 16 | Practical Training Fee | Webpage | https://isss.oie.gatech.edu/isss/ptf |
| 17 | Curricular Practical Training (CPT) | Webpage | https://isss.oie.gatech.edu/content/curricular-practical-training-cpt-georgia-tech |
| 18 | Optional Practical Training (OPT) | Webpage | https://isss.oie.gatech.edu/node/3142 |
| 19 | OPT Workshop | Webpage | https://isss.oie.gatech.edu/isss/opt |
| 20 | OPT Employment Types and Requirements | Webpage | https://isss.oie.gatech.edu/isss/types-work-constitute-employment-opt-evidence-employment |
| 21 | OPT Frequently Asked Questions | Webpage | https://isss.oie.gatech.edu/node/3456 |
| 22 | OPT and Traveling Abroad | Webpage | https://isss.oie.gatech.edu/node/3622 |
| 23 | STEM OPT Extension | Webpage | https://isss.oie.gatech.edu/content/stem-opt-extension |
| 24 | H1B Cap-Gap Extension | Webpage | https://isss.oie.gatech.edu/node/3864 |
| 25 | Professional Development | Webpage | https://isss.oie.gatech.edu/professional-development |

---

## Chunking Strategy


**Chunk size:** 800 characters (ceiling, chunks may be shorter if a natural boundary falls earlier)

**Overlap:** 150 characters

**Reasoning:**: A recursive character splitting strategy was used rather than a fixed-length strategy. More specifically, the chunker should first attempt to split on double newlines (`\n\n`), which correspond directly to the heading and paragraph boundaries encoded during the HTML-to-text conversion step. It only falls back to single newlines (list items), then sentence endings, then word boundaries if a block still exceeds 800 characters. This means a self-contained policy paragraph or FAQ answer is kept as a single chunk whenever possible, rather than being cut mid-rule.

The 800-character ceiling was chosen because the source documents consist of policy paragraphs and FAQ entries that average 400–900 characters each. A 800 character celing is large enough to hold a complete rule with its conditions. The 150-character overlap prevents a condition stated at the end of one chunk from being severed from the consequence that starts the next (e.g., "students authorized for more than 364 days of full-time CPT are no longer eligible for OPT" spanning a boundary).

Preprocessing before chunking: the HTML-to-structured-text conversion (described in the Document Sources section above) was the primary preprocessing step. Each document also retains a `Source:` and `URL:` header that is prepended to every chunk at ingest time, ensuring every retrieved chunk carries its own citation regardless of where it lands after splitting.

**Final chunk count:** 



---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
