# Book-page cataloguing task

You are cataloguing pages from a personal reading archive so they can be built into a
knowledge graph. Look at each image and record what is THERE. **Do not transcribe it.**

## Input
A JSON array (path given in your dispatch). Each entry has `path` (an image), `ocr_text`
(text already extracted), `ocr_chars`.

For EACH entry, use the Read tool to view the image at `path`, then emit six fields.

## Fields

**annotations** — `true` if the ARCHIVE OWNER marked this page.
- Counts: highlighting of ANY colour **including grey/blue low-saturation e-reader bands**,
  underlining, margin notes, hand-drawn arrows/brackets/circles/stars, bookmark flags,
  dog-eared corners.
- Does NOT count: the document's own printed design (publisher rules, a deck author's
  callout box); highlighting inside a screenshot of someone else's content; form
  completion (signatures, checkbox X-marks on a tax form or lease are not reading markup);
  highlighting in a working document the reader is *authoring* rather than reading.
- **TRAP — Kindle popular highlights.** A band with a visible crowd label
  ("3,940 highlighters") is OTHER readers' highlighting, not the reader's. Score `false`
  and say so in your summary.
- Beware screen glare: a curved bright streak at a page edge is not a highlight.

**highlight_colors** — array of colours seen: `["yellow"]`, `["yellow","pink"]`, `["grey"]`.
Empty if none. **Dark mode renders yellow as dark olive — record it as yellow, not a new
colour.**

**GREY IS USUALLY NOT A HIGHLIGHT.** It has three sources and only one is a real mark:
1. *Text-selection residue* — a grey band left by an active text selection when the
   screenshot was taken. **Proven**: another agent found the same sentence captured twice,
   plain yellow in one shot and yellow-plus-grey in the other. A grey band on the first
   line of a page, on a 3-5 word fragment, or overlapping an existing yellow highlight is
   almost always this. Do NOT record it.
2. *E-ink / greyscale device rendering* — a real highlight that the device draws in grey
   because it has no colour. Record it, and say the page is an e-ink photo in your summary.
3. A genuine grey highlighter — rare.
Record grey only for a standalone, complete, deliberate-looking band (2 or 3). When in
doubt, leave it out: a false grey is worse than a missed one, because it invents a signal.

**marks** — array from: `highlight`, `underline`, `margin_note`, `arrow`, `bracket`,
`bookmark_flag`, `circle`, `star`, `dog_ear`. Empty if none.
Note: in Apple Books a **dotted underline beneath a highlight means a written note is
attached** — record `underline` and mention it.

**book** — the title, from running header, cover, or content. e.g. `"Meditations"`,
or with author `"Meditations — Marcus Aurelius"`. **Empty string if you cannot tell from the image —
do not guess from resemblance.** Not every page is a book; work documents, forms and
screenshots turn up in a photo roll. Empty `book` + `annotations: false` is the right answer for those.

**gist** — ONE substantive sentence, your own words, on what this page is actually about.
This is used to find related pages later, so be specific ("retiring into oneself as a daily
practice rather than an escape") not generic ("a page about business"). Do not quote the page.

## Output
JSONL, one object per line, keys exactly: `path`, `annotations`, `highlight_colors`,
`marks`, `book`, `gist`. `path` verbatim from input. **Append after EACH image** so partial
progress survives a failure. On read failure write a line with `"annotations": null` and an
`"error"` key, then continue.

Oversized/HEIC images have a pre-made proxy at
`$RG_OUT/proxies/<basename>.jpg` — read that if the
original fails, but always record the ORIGINAL path.

## Return
Only: images processed, how many annotated, distinct book titles with a count each, and
any systematic pattern worth knowing.
