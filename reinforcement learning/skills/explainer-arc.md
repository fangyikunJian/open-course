# The arc of a knowledge-point video

For the case where the deliverable is a short video explaining one knowledge
point, and especially where it is one episode in a series.

Read this alongside `references/manim.md`. That file says how to build the
frames; this one says what order the ideas arrive in. The ordering matters more:
the largest effect in this whole evidence base comes not from animating, but
from confronting the viewer's wrong model (d ≈ 0.79–0.83, against d ≈ 0.37 for
animation over static). A well-animated video that skips that beat will lose to
a plainly-drawn one that includes it.

## The six beats

**The unit of the budget follows the medium.** Continuous video with narration is measured in seconds; a keyboard-advanced still-frame screening **has no seconds** — measure it in **shots + words + per-shot animation milliseconds**.

In that medium, read the six-beat budget as:

| Beat | Shots | Narration words |
|---|---|---|
| 1 Hook | 1 shot | ≤ W |
| 2 Wrong answer | 1 shot | ≤ W |
| 3 Setup | 1 shot | ≤ W |
| 4 Body | 2–4 shots | ≤ W × shots |
| 5 Refutation | 1 shot | ≤ W |
| 6 Prompt and final still | QUIZ + SUM | SUM ≤380 words total, ≤110 per column; QUIZ ≤300 words total |

**W is not to be guessed.** The caption band occupies y=480–676 at 1440×900 (196 px tall); before any work starts, measure how many words that band actually holds without scrolling, put the number in this table, and assert it the way the SUM card does, with `scrollHeight ≤ clientHeight + 2`.

**What "one idea per segment" means in this engine**: one knowledge point is ≤12 shots, and the `S(t)` timecode spread between the first and last shot is ≤360 s.

**Add the one quantity that actually needs governing and that the previous version lacked entirely: per-shot animation wall-clock duration ≤4000 ms (>6000 ms = BLOCK).** Sum it statically from each primitive's defaults: `trace (dur||2.4)×1000`, `morphBars dur||1400`, `fillBars len(order)×(step||260)+320`, `sweepGrid len(order)×(step||190)+300`, `reveal n×(step||240)+340`. The reason: advancing is **manual**, and no reader sits through a five-second sweep — a 25-cell sweepGrid is 25×190+300 = 5050 ms, the reader hit space long ago, and that shot's conclusion never arrived. This quantity can be computed without running anything, and nobody has ever computed it.

**Never carry two sets of units side by side in one rule.** The PROJECT §1 table listed "≤30s" next to "one `S()` shot"; one of the two had no criterion behind it, and the result of listing both is that the executor takes neither seriously. **Delete the one without a criterion — do not keep it "for reference".** The same applies to "the whole thing stays under six minutes", "Motivation lands in the first 30 seconds", and "video segments are under six minutes" in SKILL.md: restate each as a shot count (motivation lands in shot 1).

**Every content criterion in the six beats stays, word for word — only the seconds are deleted.**

Total 3–6 minutes. Longer topics become two episodes, not one long one.

### 1. Hook — the question (≤ 30 seconds)

Pose the specific question this episode answers. Not "today we'll look at ridge
regression" — the actual question: *why does adding a penalty make coefficients
smaller rather than just different?*

Owes: within thirty seconds, the viewer knows why they should care. This is the
criterion working expositors judge on, and it is where most academic explainers
lose people.

### 2. The wrong answer — say it out loud (30–45 seconds)

State the plausible-but-wrong model, and state it *sympathetically*, so a viewer
who holds it recognises their own thinking. Do not signpost it as wrong yet.

This is the beat almost everyone skips, and it is the highest-value one in the
episode. In a randomised study of 364 first-year physics students, a version
that stated and refuted common misconceptions beat a clear conventional
exposition of the same content with an effect size of about 0.79; a
student–tutor dialogue version reached about 0.83. Low-prior-knowledge students
gained most, and high-prior-knowledge students were not harmed by it.

The mechanism matters for how you write it: a clean exposition feels clearer to
the viewer and takes less effort, and that is exactly the problem. Without a
collision against their existing model, the viewer files the new explanation
next to the old one instead of replacing it, and comes away confident and
wrong.

**If you cannot name a wrong model, look harder.** Candidates: what students
write in exams, what the notation invites you to assume, the special case people
over-generalise from, the neighbouring concept people confuse this with (ridge
vs lasso, correlation vs causation, "the dual is just a trick"). If there is
genuinely no misconception, this knowledge point is a definition rather than a
concept — then use the naive question a student would actually ask instead.

### 3. Setup — name the pieces (30–45 seconds)

Introduce and label every object and symbol that will appear, before any of them
does anything. People learn better from a lesson when they already know the
names and characteristics of the key concepts.

Never introduce a new symbol and a new process in the same beat. This is also
where you state the assumed background out loud, since the right amount of
scaffolding differs sharply by prior knowledge.

### 4. The body — concrete, then the move, then abstract (90–180 seconds)

Three sub-beats, in this order:

- **A concrete case.** One instance, with actual numbers or an actual picture.
  Not the general form.
- **The move.** The construction, the transformation, the argument. This is
  where the aha lives. Build cumulatively, cue dynamically, and keep everything
  needed for comparison permanently on screen.
- **The fade to abstract.** The general symbol appears *while the concrete case
  is still visible*, so the two are seen as the same object. Undergraduates
  taught this way had better transfer than either concrete-only or
  abstract-only groups, immediately and three weeks later.

One aha per episode. If the body contains two, it is two episodes.

### 5. The refutation — go back and kill the wrong model (≈ 30 seconds)

Return explicitly to beat 2 and say why that intuition failed, in terms of what
was just built. Not "so as you can see" — name the wrong model again and show
precisely where it breaks.

An episode that opens a misconception and never closes it is worse than one that
never opened it.

### 6. The prompt and the final still (≈ 30 seconds)

- **A generative prompt.** A question the viewer answers before the episode
  ends: predict, or "what changes if this term goes to zero". Watching is the
  weakest mode of engagement there is; one step up is the cheapest quality gain
  available.
- **The final still.** The last frame is a complete figure that stands alone.
  Export it (`manim -qh -s`) and ship it with the video — it is what people
  screenshot, and it is the artefact that survives after the motion is gone.

## Series consistency

For a series of knowledge-point episodes, fix these once and never revisit them
per episode. Consistency across episodes is itself instructional: viewers stop
spending attention on decoding the format.

- **Palette.** One colour per *quantity*, held across the whole series, not per
  episode. Residuals are the same colour in every video they appear in.
- **Layout regions.** Same title strip, same permanent region corner, same
  prompt position, every episode.
- **Beat structure.** The six beats above, in the same order, every time.
- **Opening and closing.** Same shape, so the hook and prompt are recognisable
  as beats rather than as content.
- **Naming.** Same symbol conventions as the course or textbook the viewers are
  actually using. Do not invent a competing notation for elegance.

## Per-episode spec sheet

Fill this before writing any code. It is the whole of Steps 1–3 for a video, on
one page, and it is what makes the series repeatable.

```
EPISODE:        <knowledge point>
AUDIENCE:       <who, and what they already know>
QUESTION:       <the hook, as a question>
WRONG MODEL:    <the misconception, stated sympathetically>
WHY IT FAILS:   <the refutation, one sentence>
OBJECTS:        <every symbol/shape to pre-train, in order of appearance>
CONCRETE CASE:  <the specific instance>
THE MOVE:       <the construction that carries the aha>
THE AHA:        <one sentence>
ABSTRACTION:    <the general form it fades into>
PROMPT:         <what the viewer does>
FINAL STILL:    <describe the frame that must stand alone>
ARCHETYPE:      build | sweep | transformation
RUNTIME:        <target, under 6 min>
```

If any line is empty, do not start building. An empty WRONG MODEL line in
particular means the episode will be clear, pleasant, and less effective than
it could be.
