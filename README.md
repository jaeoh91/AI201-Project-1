# Project 1: F-1 Visa RAG Knowledge Base


## Domain

Policies & Regulations relevant to international students on a F1 Visa (the most common student visa type) at Georgia Tech.

---

## Document Sources

All sources from policy documents provided by the Georgia Institute of Technology's Office of International Education, International Student & Scholar Services. (Link: https://isss.oie.gatech.edu/ISSS_F_Current)

Wrote a simple python script (`download_sources.py`) to scrape each website, and download only the policy text (avoiding links, banners, and other elements on the website that could add junk data). 

Additionally, to aid with the recursive chunking strategy we implement later, we went beyond simply copying the website text (which in testing resulted in broken sentences and overall messy formatting that would be problematic for any chunking strategy). Instead, the script walks the HTML tree tag-by-tag and converts each element into structured plain text similar to markdown: headings (`<h1>`–`<h6>`) become `# Heading` lines surrounded by blank lines, paragraphs (`<p>`) are separated by double newlines, list items (`<ul>`/`<ol>`) are rendered as `- item` or `1. item` lines, and tables are flattened into pipe-separated rows. Navigation elements, banners, scripts, and footers that would add junk data to our documents are stripped entirely. 

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

**Embedding model:** `all-MiniLM-L6-v2`
- very lightweight
- low context window (256 tokens), but perfect for 800 character chunk size

**Top-k:** 10, but with cosine distance filter afterwards.
- Chose a pretty generous top-k because student-visa related policy questions often cross multiple topics / policies. (ex: `Can I work on CPT for 2 years and apply for OPT later?` would require knowledge about different topics including CPT, OPT, post-completion OPT, and STEM OPT extension)

**Production tradeoff reflection:**
Without practical constraints, I would change my approach based on these considerations:
- Domain Knowledge: A model fine tuned on legal / policy documents would result in more accurate embeddings. A general purpose model would not know, for instance, that "SEVIS", "DSO", and "I-20" are semantically close terms in a immigration context
- Multilingual: I would also consider adding multilingual prompt support to allow users to prompt in their native languages. A multilingual model such as `multilingual-e5-large` would allow users to do so

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
Full System Prompt:
```
You are an expert assistant on F-1 visa policy for Georgia Tech international students.
Answer the user's question using ONLY the information provided in the numbered context
passages below. Do not use any outside knowledge about immigration law or visa policy.

Rules:
1. Cite the source inline immediately after each sentence that contains a factual claim.
   Format citations as a Markdown link using the source name and URL from the passage header,
   e.g. "Students authorized for more than 364 days of full-time CPT are no longer eligible
   for OPT. ([Curricular Practical Training (CPT)](https://isss.oie.gatech.edu/content/curricular-practical-training-cpt-georgia-tech))"
2. If the context passages do not contain enough information to answer the question,
   respond with exactly:
   "I'm sorry, I don't have enough information in my knowledge base to answer that question. \
Please contact GT ISSS directly at isss@oie.gatech.edu for authoritative guidance."
3. Do not infer, guess, or extrapolate beyond what is explicitly stated in the passages.
4. Do not mention the context numbers or that you were given passages — answer naturally.
```

**How source attribution is surfaced in the response:**
The first rule in the system prompt enforces source attribution. Specifically, I prompted the LLM to attach citations immediately after each sentence (without this clarification, the model was attaching citations at random points of the response), and to format the citations in markdown link format so that the user can click on the link to visit the official GT policy document where the model is drawing its response from. The implementation of the URL attribution was possible because when we scraped the document, we attached the document name & origin URL to the document, then to each chunk in the ingestion stage.
```
1. Cite the source inline immediately after each sentence that contains a factual claim.
   Format citations as a Markdown link using the source name and URL from the passage header,
   e.g. "Students authorized for more than 364 days of full-time CPT are no longer eligible
   for OPT. ([Curricular Practical Training (CPT)](https://isss.oie.gatech.edu/content/curricular-practical-training-cpt-georgia-tech))"
```

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | I am an international student on a F1 visa. I worked for 400 days on full-time CPT. Am I eligible for OPT after graduation? | No, since you participated in more than 364 days of full-time CPT, you are not eligible for OPT. | `Students who have participated in more than 364 days or more of full-time CPT are ineligible for OPT. Since you worked for 400 days on full-time CPT, you are not eligible for OPT.` | Partially relevant, the answer was in chunk #8, and all chunks had pretty similar distances (0.3~0.4) | Accurate
| 2 | I worked for 4 academic semesters on part-time CPT, and 2 summers on full-time CPT (around 3 months each). Am I all good for OPT after graduation? | Yes, part-time CPT does not count towards your CPT limit. You completed around 6 months of full-time CPT, which should be well under the 364 day limit that would make you inelligible for OPT. | Part time doesn't impact + you worked for 6 months + under 364 day limit -> You're eligible | Partially relevant, chunk #5/5 had the answer & it had a distance of 0.49 (almost got filtered) | Accurate
| 3 | I'm a F1 student who recently began work on-campus as a student employee. Do I need an SSN? How do I get one? | You don't need one under federal law, but GTHR requires you to obtain one and provide it within 90 days of your start date. [instructions to get one] | (*Response actually corrected my misunderstanding*) SSN required by federal law + GTHR, here's detailed step by step instructions on how to obtain | Relevant (all 9 chunks) | Accurate 
| 4 | I'm on post-completion OPT and my F-1 visa stamp expired. I want to visit my family abroad for 3 weeks and come back. What do I need to do before re-entering the U.S.? | You must obtain a new F-1 visa before attempting to re-enter the U.S. — an expired visa stamp is not valid for re-entry even while on OPT. The one exception is Automatic Visa Revalidation, which allows re-entry with an expired visa only if you visited Canada, Mexico, or adjacent islands (excluding Cuba) for fewer than 30 days total and did not apply for a new visa during that trip. | You need to apply for new visa | Partially relevant, correctly retrieves the visa renewal necessity, but misses the AVR exception on the next chunk | Partially Accurate (misses AVR Exception)
| 5 | I'm an F-1 student and my doctor has recommended I take a lighter course load this semester for medical reasons. Can I drop below 12 credit hours, and if so, what is the minimum I can take? | Yes, you may apply for a Medical Reduced Course Load (RCL). You must submit documentation from a licensed medical professional and receive OIE approval *before* dropping below full-time. With medical RCL approval, you can reduce enrollment to as few as 0 credits. You cannot drop below full-time before receiving the approval or you will be considered out of status. | Exact same as expected | Relevant | Accurate

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

**General Notes**: 
- The distance scores are not perfect indicators, and making the decision to be generous with the top-k was a good choice as a lot of times the key context would have the lowest distance score and be at position k-1
- 800 characters were shorter than I thought, and a lot of times did cut important context

---

## Success Case Analysis

**Question:**  `"I started my initial 12-month OPT on January 1st. I was unemployed for 30 days in February and another 20 days in May. On June 1st, I applied for a STEM extension which was approved on August 1st. Between August and October, I had a gap in employment for 45 days. If I continue working from October onwards, how many more days of unemployment can I accrue before my STEM OPT expires in two years, and does the fact that I had an EAD expiration date during that transition change how those days are counted?"`

**Why it expected it to fail**: 
- Very complicated query
- Requires LLM to track dates across a timeline & perform multi-step calculations
- Full calculation: 
```
- Initial unemployment:  30 + 20 = 50
- STEM gap: + 45 days
->Total used: 95 days.
- Limit:  150 days total.
- Remaining: 150 − 95 = 55 days
```
- Distraction question: The question about the "EAD expiration date" is irrelevant, and tests whether the model can find the specific rule that says EAD gaps during Cap-Gap or STEM transitions are handled differently.

**What the system returned:**
`You accrued 50 days of unemployment during your 12-month OPT period, 30 days in February and 20 days in May (OPT Frequently Asked Questions). After your STEM extension was approved, you accrued an additional 45 days of unemployment between August and October (STEM OPT Extension). In total, you have accrued 95 days of unemployment so far. You are allowed a total of 150 days of unemployment during your OPT and STEM OPT extension periods (STEM OPT Extension). Therefore, you can accrue 55 more days of unemployment before your STEM OPT expires in two years (Regulations Overview). The fact that you had an EAD expiration date during the transition does not change how those days are counted, as any unused unemployment days from your post-completion OPT authorization would carry over and be used during your STEM OPT authorization (OPT Frequently Asked Questions).`



## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:** 

I'm on post-completion OPT and my F-1 visa stamp expired. I want to visit my family abroad for 3 weeks and come back. What do I need to do before re-entering the U.S.?

**What the system returned:**
```
To re-enter the U.S. while on post-completion OPT with an expired F-1 visa, you are required to apply for a new F-1 visa before attempting to re-enter the U.S. (OPT and Traveling Abroad). You should review the visa requirements on the website for the appropriate U.S. Embassy/Consulate, as procedures and requirements for visas can vary between countries and are often subject to change (OPT and Traveling Abroad). You can visit www.travel.state.gov to determine the procedures for applying for a visa at the U.S. Embassy/Consulate in the country in which you’ll be traveling (OPT and Traveling Abroad). Additionally, you can visit the OIE’s Visa Renewal website for general guidance and information on visa renewals (OPT and Traveling Abroad). New visas cannot be obtained while inside the United States, so you will need to exit the U.S. and apply for the new F-1 visa at your nearest U.S. consulate/embassy (Travel).
```

**What the error is:** The LLM's answer omits an exception the user should be aware of: Automatic Visa Revalidation, which allows re-entry with an expired visa only if you visited Canada, Mexico, or adjacent islands (excluding Cuba) for fewer than 30 days total and did not apply for a new visa during that trip.

**Root cause (tied to a specific pipeline stage):** Retrieval failure.
- During chunking, the general guideline for OPT & Traveling abroad got separated from the section outlining the AVR exception.
- The retrieval pipeline failed to match the chunk containing the AVR exception rule. 
- Reviewing the retrieval trace (`python retriever.py "I'm on post-completion OPT and my F-1 visa stamp expired. I want to visit my family abroad for 3 weeks and come back. What do I need to do before re-entering the U.S.?"`), we see that none of the 10(!!!) chunks matched contain the AVR exception.
- We also see that Chunk 1 (the most relevant chunk) cuts out right before the AVR exception clause. 
- Because the next chunk contains only information about the AVR exception, the retrieval pipeline was likely unable to match it to the query about OPT related travel.


**What you would change to fix it:**
- Increase Chunk Size/Overlap to increase the likelihood that a rule and its immediate exception are captured in a single context block.
- Implement "Parent Document Retrieval" (Small-to-Big), where instead of passing just the small 800-char chunk to the LLM, the system could use the small chunk for retrieval but then feed the entire section or surrounding paragraphs from the source document during the generation phase. This ensures that if a specific rule is found, its associated exceptions are also provided as context.
- Consider a semantic chunking strategy, which would ideally cluster sections containing important exceptions together with the general guidlines


---

## Spec Reflection

**One way the spec helped you during implementation:**
- I went through a iterative process of planning out my what my application would look like, starting from a problem statement, going to high level strategies, to system design, and then finally technical implementation after I had a complete system-design document (see `system-design.md` and a completed `planning.md` document) 
- This helped me think more critically about the design choices I was making & helped me learn a lot more about the tools & frameworks my appication used
- Also, this helped me craft more effective and specific prompts to LLMs compared to just prompting it to "create an application"

**One way your implementation diverged from the spec, and why:** 
- Initially planned to cite the source by name, but found that this really didn't make sense because something like (Source: OPT and Travel) would give very little context or confidence to the user without access to the referenced document. I came up with the idea to link the relevant website to allow the user to actually visit the website containing the relevant policy document
-  Initial top-k was 5, but after testing sample queries, found that a lot of times, relevant context was found in chunk >5 -> decided to refine it to 10.
---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

- Experimented with various models
- Claude Sonnet 4.6 for heavy lifting tasks, self-hosted Gemma 4 31b instance for general tasks, and also tried out Claude's newly released Fable 5.
- For model interfaces, used GitHub copilot in both Agent and Ask mode (depending on the task) and experiemented with Cursor's Agent & Code review modes

**Instance 1**

- *What I gave the AI:* `planning.md` + "Based on the use case and specs provided in the document so far, come up with a effective chunking strategy"
- *What it produced:* A fixed-size chunking strategy, 800 char + 150 overlap window.
- *What I changed or overrode:* 
     - Followed up with a prompt asking the model to compare and contrast the benefits and downsides of alternative strategies
     - Decided to proceed with a recursive chunking strategy

**Instance 2**

- *What I gave the AI:* 
     1.  Markdown table of source document names + urls
     2. Prompt `"write a python script to download text from each of these sources and store it in /documents"`
- *What it produced:*: A basic python script to scrape text from the website and store it to .txt files
- *What I changed or overrode:*
     1. Upon inspection of the `.txt` files, found that there was a lot of junk data from banners, links, etc & that the formatting of the text was messed up and contained a lot of random line breaks. By contract, the policy document websites had content well organized under headings, sub-headings, lists, etc. -> Looked into the HTML structure of the website -> prompted the website to preserve website & text structure and fed them few-shot examples of html structure from one of the policy doc websites -> led to "smarter", structure-aware scraping
     2. Refined the script to include the URL & the document title at the top to aid in the retrieval & generation steps.
