# Project 1: F-1 Visa RAG Knowledge Base


## Domain

Policies & Regulations relevant to international students on a F1 Visa (the most common student visa type) at Georgia Tech.

---

## Document Sources

All sources from policy documents provided by the Georgia Institute of Technology's Office of International Education, International Student & Scholar Services. (Link: https://isss.oie.gatech.edu/ISSS_F_Current)

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

## Chunking Strategy: Recursive Chunking

**Chunk size:** 800 characters (ceiling, chunks may be shorter if a natural boundary falls earlier)

**Overlap:** 150 characters

**Why these choices fit your documents:** A recursive character splitting strategy was used (`separators = ["\n\n", "\n", ". ", " "]`) rather than a fixed-length split. The chunker first attempts to split on double newlines (`\n\n`), which correspond directly to the heading and paragraph boundaries encoded during the HTML-to-text conversion step. It only falls back to single newlines (list items), then sentence endings, then word boundaries if a block still exceeds 800 characters. This means a self-contained policy paragraph or FAQ answer is kept as a single chunk whenever possible, rather than being cut mid-rule.

The 800-character ceiling was chosen because the source documents consist of policy paragraphs and FAQ entries that average 400–900 characters each — large enough to hold a complete rule with its conditions, but small enough that an LLM context window can comfortably fit 3–5 retrieved chunks. The 150-character overlap prevents a condition stated at the end of one chunk from being severed from the consequence that starts the next (e.g., "students authorized for more than 364 days of full-time CPT are no longer eligible for OPT" spanning a boundary).

Preprocessing before chunking: the HTML-to-structured-text conversion (described in the Document Sources section above) was the primary preprocessing step. Each document also retains a `Source:` and `URL:` header that is prepended to every chunk at ingest time, ensuring every retrieved chunk carries its own citation regardless of where it lands after splitting.

**Post-processing — orphaned heading fix:** Inspection of the initial chunks revealed that when a body paragraph ended exactly at the 800-character ceiling, the splitter placed the next section heading at the tail of the current chunk with no content beneath it. A retrieved chunk consisting solely of a citation header and a bare heading line is semantically useless to the LLM. A second pass detects these cases and moves the orphaned heading forward to the top of the following chunk, keeping headings co-located with the content they introduce.

**Final chunk count:** 494

```
Loading and chunking 25 documents...
  01_regulations_overview.txt: 22 chunks
  02_f_immigration_document_overview.txt: 11 chunks
  03_enrollment_requirements.txt: 23 chunks
  04_understanding_your_i_20_ds_2019.txt: 22 chunks
  05_i_20_updates_keeping_your_i_20_up_to_date.txt: 14 chunks
  06_digitally_signed_i_20_form_guidance.txt: 7 chunks
  07_travel.txt: 43 chunks
  08_renewing_your_visa.txt: 11 chunks
  09_taxes_for_non_residents.txt: 16 chunks
  10_change_of_status_to_f_1.txt: 14 chunks
  11_transfer_sevis_record_to_another_u_s_institution.txt: 10 chunks
  12_change_of_status_from_f_1.txt: 7 chunks
  13_out_of_status_options.txt: 18 chunks
  14_social_security_numbers.txt: 12 chunks
  15_f_1_employment_overview.txt: 12 chunks
  16_practical_training_fee.txt: 10 chunks
  17_curricular_practical_training_cpt.txt: 60 chunks
  18_optional_practical_training_opt.txt: 55 chunks
  19_opt_workshop.txt: 5 chunks
  20_opt_employment_types_and_requirements.txt: 13 chunks
  21_opt_frequently_asked_questions.txt: 15 chunks
  22_opt_and_traveling_abroad.txt: 15 chunks
  23_stem_opt_extension.txt: 63 chunks
  24_h1b_cap_gap_extension.txt: 12 chunks
  25_professional_development.txt: 4 chunks
```

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**

**Production tradeoff reflection:**

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**

**How source attribution is surfaced in the response:**

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |
| 4 | | | | | |
| 5 | | | | | |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**

**What the system returned:**

**Root cause (tied to a specific pipeline stage):**

**What you would change to fix it:**

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**

**One way your implementation diverged from the spec, and why:**

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*

**Instance 2**

- *What I gave the AI:*
- *What it produced:*
- *What I changed or overrode:*
