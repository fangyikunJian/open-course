---
name: teaching-viz
description: Plan and build visual explanations of mathematical, statistical and machine-learning ideas — Manim animations, static figures, and the explanation scripts behind them — using evidence-based instructional-design rules instead of defaulting to animation. Use this skill whenever the user wants to explain, teach, illustrate, animate, or visualise a concept, derivation, proof, algorithm, or formula; whenever they mention Manim, 3Blue1Brown-style videos, explainer videos, lecture visuals, tutorial figures, teaching slides, or course/tutoring material; and whenever they ask "how do I show X" or "how do I explain X" — even if they never say the words "animation" or "visualisation". Use it for a single diagram as readily as for a full video.
---

# Teaching Visualisation

## Core stance

The explanation is the product. The medium (animation, figure, interactive) is a
delivery decision made *after* the explanation exists. Visuals almost never fail
because the code was bad; they fail because nobody decided what one idea the
viewer should walk away with, or because animation was chosen when a labelled
static figure would have taught more.

The empirical picture is deflating and should be treated as the baseline
assumption: across meta-analyses, animation beats static graphics by only a
small-to-medium margin (d ≈ 0.37; g ≈ 0.23), and the advantage concentrates in
*representational* animation of things that genuinely change over time. Motion
that decorates rather than represents buys nothing and costs working memory.
See `evidence.md` for the full basis of every rule below.

Three non-negotiables:

1. **Choose the medium at Step 2, before writing any code.** Animation must be
   earned by the congruence test, not assumed.
2. **Every deliverable carries one aha and one generative prompt.** Passive
   watching is the weakest learning mode there is.
3. **Never ship a frame you have not looked at.** Rendering is not checking.
   Layout collisions are the single most common failure of generated animation.
**Any clause written as "not optional" must come with a fallback ladder and a
disclosure obligation.**

A mandatory clause that is physically impossible to execute in some environments
does not raise quality in those environments — it teaches the executor to declare
a silent pass, and that habit contaminates every other item on the list. So
wherever you write "not optional", "must", "never omit" or "always", the same
passage has to answer three questions:

1. **What is the precondition?** State it as a measurable quantity (example:
   rAF fires more than 0 times in 700 ms).
2. **What do you fall back to when the precondition does not hold?** Name the
   next rung down, and say what that rung covers and what it gives up.
3. **What must be disclosed after falling back?** Give the sentence that has to
   go into the delivery note verbatim.

**This pack already contains one example that gets the template right; copy it:**
beat 2 of `explainer-arc.md`, "**If you cannot name a wrong model, look
harder.**" It gives the candidate list first (what students write on the exam,
what the notation invites you to assume, the special case that gets
over-generalised, the neighbouring concept that gets confused with this one),
then the real fallback path ("if there truly is no misconception, this is a
definition rather than a concept — switch to the naive question a student
actually asks"). Precondition, fallback target and coverage are all there, and it
is the **only** clause in the whole skill that is both mandatory and carries a
fallback.

**The counter-example is in the same file:** "Render, then look at the frames.
This step is not optional and not delegable" — no precondition, no fallback, no
disclosure, and its precondition measures false in this environment
(`document.hidden=true`, rAF fires 0 times in 700 ms).

**"Not delegable" is itself pointed the wrong way in an environment that cannot
see**: what must not be delegated is the **mechanical check** (it has to actually
run; reporting it from memory does not count), and what must be delegated is
exactly looking at the picture. The previous version had the two backwards, so
the executor met a requirement it could neither execute nor hand off, and skipped
the clause whole.


## Workflow

Follow all five steps in order. Do not skip to Step 4 because the user asked
for "a Manim animation of X" — they are describing a medium, not a brief.
If the user's request is already precise about audience and message, Step 1
can be one short paragraph, but it still gets written.

### Step 0 — Engine measurement inventory (the first step when medium and engine are both given)

The medium gate has **three** modes, not two:

1. **Medium undecided** → the four questions are a decision tool. Run Q1–Q4 and
   record which one decided it.
2. **Medium fixed, the tooling still to be built** → the four questions are a
   design spec. Run the "Would have failed → So the animation must" table.
3. **Medium and engine both given and already in existence** → **the four
   questions cannot help.** The real constraint is what the engine has been
   measured to do, and not one of the four can ask whether `flip()` typesets
   LaTeX. Do Step 0 first, then enter Step 1.

What Step 0 produces is a **written table**, not an impression in your head. It
is this project's build spec — the skill ships no medium template, and the
output of Step 0 fills that slot. Six rows; with any one missing you do not enter
Step 3:

| Row | What goes in it | How you get it |
|---|---|---|
| **Primitive inventory** | Every callable primitive: its name, its **parameter count**, and a one-sentence "what it actually does" written **after reading the implementation** | Read each implementation. No inferring from the function name — measured cost: we assumed `flip()` typesets LaTeX; in fact `setEq()` calls `MathJax.typesetPromise` while `flip()` only does `innerHTML=h`, and raw backslashes showed up on screen |
| **Typesetting/DOM behaviour, and why it cannot be changed** | Which primitives go through MathJax, which only write innerHTML, which animate by measuring positions off `[data-id]` nodes | Same as above. Also record why it **cannot** be changed: `flip` cannot be moved onto MathJax because it measures positions off `[data-id]`, and MathJax rebuilds the DOM. Corollary: `flip` only holds **within a single shot** — `go()` runs `setEq(null)` to clear eqBox before drawing each shot, so a cross-shot flip yields a fade-in and nothing more; the displacement animation is structurally impossible (all 3 flips in the film are cross-shot, and their teaching payload is empty) |
| **Primitives that return a coordinate transform** | Which primitives return a mapper, and what they return | `errbar` returns `{Y,x0,w}`; `gridworld`/`sweepGrid` return `{x0,y0,cs,cx,cy}`; `mdpChain` returns `pos` |
| **Layout budget** | The y/x interval of every fixed band at the target viewport, written as numbers | Measure `getBoundingClientRect()` in the **real viewport**. Do not measure the design mockup, and do not measure a scaled preview panel |
| **Where the content authoritatively lives** | Which file is the single truth for content (in this project the JSON, not the assembler source) | Every checker must point at it and print the list of files it actually read |
| **Animation drive mechanism and observability** | rAF / CSS / setTimeout; and whether it can be observed in the current checking environment | Measure `document.hidden` and how many times rAF fires in 700 ms. This cell decides which rung of the Step 5 fallback ladder you land on |

**Concretely, what you do first: read the implementations and write out the
primitive inventory.** Not measure the layout first — the layout budget can only
be fixed once you know the primitives (how much `setEq(...,"top")` occupies,
whether the caption band shows by default), so reading implementations comes
before anything else.

**And add one more non-negotiable (Core stance, as item 3; the old item 3 drops
to item 4):**

> **Before you call any existing primitive, read its implementation.** Do not
> infer behaviour from the function name, and do not infer it from what a
> primitive of that name usually means elsewhere. When you have read it, write
> "what it actually does" as one sentence into the Step 0 primitive inventory.
> **Not in the inventory = not read.**

### Step 1 — Write the brief (always, before anything else)

Produce these six lines and show them to the user. They are cheap to fix now
and expensive to fix after rendering.

| Field | What goes in it |
|---|---|
| Audience | Who, and specifically what they already know. Prior knowledge changes the right design more than any other variable. |
| Prior representation | What notation/picture they have already met for this topic. Build on it; do not invent a competing one. |
| Message | One sentence: what they should be able to do or see afterwards. If it needs "and", split into two deliverables. |
| Motivation | One sentence answering "why should I care", deliverable in the first 30 seconds. |
| Misconception | The wrong mental model this is fighting, stated sympathetically. Not optional: explicitly refuting the viewer's wrong model is the largest single effect in the evidence base, roughly twice the size of animating at all. If you cannot name one, look harder before concluding there isn't one. |
| The aha | The single moment of insight. One per deliverable. |

Then state the assumed prior knowledge *in the deliverable itself*. Novices and
experts need opposite amounts of scaffolding, so the artefact should say who it
is for.

### Step 2 — The medium gate

Run these tests in order and stop at the first that fires.

**First, check whether the medium is already decided.** It is decided if the
user asked for an animation, if the piece is an episode in an existing animated
series, if the brief or the project is *about* making animations, or if the
output has to match material that already exists. In that case the gate is not
a decision and must not be run as a veto. Say in at most one sentence what the
questions below would have flagged, then go straight to
**"Animation with the medium locked"** and spend the effort on making the
animation good. Talking someone out of the medium they came for is not help.

Only when the medium is genuinely open, run these four questions in order.

**Q1 — Congruence.** Does the content contain change over time, a process, a
causal chain, or a construction order?
- **No** → a static figure (this pack ships no code template for static figures;
  how you draw it comes from the Step 0 engine inventory). Most algebraic
  identities, most structural relationships, and most "which of these is bigger"
  arguments land here.
- **Yes** → Q2.

**Q2 — Simultaneity.** Could everything the viewer needs to compare be shown
legibly *at the same time*, on one page — as a path, a strip, or stacked lines?
- **Yes** → static wins by default, and animation now has to earn its place by
  adding something the still cannot give. Q1 is easy to pass: a parameter sweep,
  a derivation, and a proof all contain order. This is the question that
  actually decides most cases, because a still keeps every state permanent while
  an animation takes that away.
- **No** → Q3.

**Q3 — Apprehension.** Can a first-time viewer follow the change at the speed
it happens?
- **No** → decompose into discrete beats. Continuous processes are usually
  understood as a series of discrete states anyway, so the strip or the
  beat-by-beat build may be the *congruent* form, not a downgrade.
- **Yes** → Q4.

**Q4 — Manipulation.** Would the learner want to move a parameter themselves?
- **Yes** → an interactive beats a video of you moving the slider. This version
  does not build interactives: say so, and deliver the parameter sweep with a
  summary frame (see below) as the closest substitute.
- **No** → animate.

Record which question decided it, in one line.

### Animation with the medium locked

When animation is given rather than chosen, the four questions stop being
vetoes and become the design spec. Run them silently anyway: each one that
*would* have failed names a specific thing this animation has to do in order to
survive the objection behind it. This is where most of the value of the skill
sits for animation work.

| Would have failed | So the animation must |
|---|---|
| **Congruence** — the idea does not inherently move | Use motion for *construction order and attention routing*, not to fake dynamics. The honest form is the progressive build: animate the assembly of a figure that ends as a still. Do not invent movement the mathematics does not have. |
| **Simultaneity** — the whole thing would fit on one page | Build cumulatively and never erase. The final frame should be the figure you would have drawn anyway, and should stand alone. Animation earns its keep by controlling the *order* in which attention arrives, which a still cannot do. Export that last frame as a figure too. |
| **Apprehension** — too fast or too dense to follow | Discrete beats with real holds between them. One change per beat, and a wait after every reveal. |
| **Manipulation** — the learner wants a slider | Parameter sweep: hold at three named values rather than sliding continuously past everything, leave a visible trace of where the sweep has been, and end on a summary frame showing the key values together. |

Three archetypes cover nearly all mathematical animation. Name which one you
are building before writing code; mixing them inside one segment is a common
way to lose the viewer.

1. **Progressive build** — a still figure assembled one element at a time.
   For structural arguments. Requirement: nothing ever leaves; the last frame
   is a complete, self-sufficient figure.
2. **Parameter sweep** — one quantity varies, everything else holds.
   For λ, for a hyperparameter, for an angle. Requirement: a trace, named
   holds, and a summary frame.
3. **Transformation** — one object becomes another, and the motion *is* the
   argument. For change of basis, for a substitution, for a proof step.
   Requirement: both endpoints readable during the motion, or show them side
   by side and animate the correspondence instead.

The implementation details of the three archetypes come from the Step 0 engine
measurement inventory — which primitives express which archetype, and what their
parameters and real behaviour are. This pack binds to no particular engine.

### Step 3 — Segment and storyboard

**If the deliverable is a video explaining one knowledge point, read
`explainer-arc.md` now** and fill in its per-episode spec sheet
instead of improvising the structure. It gives the six-beat arc, the time
budget, and the series-consistency rules. The rest of this step still applies.

**Segment.** One idea per segment. If the deliverable is a video, each segment
is a natural stopping point and the whole thing stays under six minutes;
longer topics become several short pieces, not one long one. Short segments are
the single most reliable fix for the working-memory cost of moving pictures.

**Order.** Structure the explanation concrete → intermediate → abstract, and
make the fading explicit: keep the concrete instance visible while the general
symbol appears, so the two are seen as the same thing. Jumping straight to the
general symbol is the default failure of mathematical exposition.

**Pre-train.** Name and show every object before showing what it does. Never
introduce a new symbol and a new process in the same beat.

**Storyboard.** For each segment write a three-column table before touching code:

| On screen | Said / captioned | Stays or goes |
|---|---|---|

Rules for that table:
- Anything that must be compared later goes in "stays".
- Words go next to the thing they label, not in a legend elsewhere.
- Narration and the visual it describes happen at the same time, not in sequence.
- Do not put the narration on screen as text as well. Duplicating spoken words
  as on-screen text hurts. Short labels are not duplication; sentences are.
- Cut anything that is interesting but not on the message. Interesting-but-extra
  material measurably reduces learning.

**Plan the generative prompt.** Decide now where the learner does something:
a predict-then-reveal pause, a "what happens if this term goes to zero", a
question posed before the answer is shown. One per deliverable, minimum.

### Step 4 — Build

**The build spec is decided by the medium; this package ships no code template
for any medium.**

- **Medium and engine both given** (this project is one of those) → the Step 0
  engine measurement inventory **is** the spec for this step: the primitives you
  may call and what they actually do, the layout budget, the closed set of font
  sizes, the container limits. Stop looking for a generic template.
- **Working in something like Manim / matplotlib** → build the template yourself
  first and treat it as a Step 0 artefact (write down the layout budget, the
  permanent-region convention, the colour rules) instead of expecting this
  package to supply one.
- Either way, this step assumes the artefacts of Steps 0–3 already exist.

## Checker self-verification (before running any check)

**Green from a checker that matched nothing is worse than no checker at all — it
stops people from checking.**

Before it prints any conclusion, every checker must first print **how many
objects it found to check** and compare that against a floor. Any count that is
0 or below the floor exits non-zero immediately with "the checker is pointed at
the wrong target": do not keep running, do not print "all passed".

Four hard requirements. Every one of them has already been paid for:

1. **Two-way gold-sample self-test.** Every checker carries two samples of its
   own: a known-compliant one that must pass, and a known-violating one that
   must be caught. Its verdicts count only once both run clean — "the compliant
   sample passes" is not enough on its own, because a checker that always
   returns "pass" clears that too. Scripts take `--selftest` and exit non-zero on
   failure; the first command before delivery is a `--selftest` run across every
   checker.
2. **Print what was actually read.** The file list plus per-file hit counts. A
   file count of 0 **must exit non-zero**. Measured cost: a lint pointed at the
   assembler source matched 0 objects on all eight checks, then printed "all
   passed." and returned 0 — the content lives in the JSON, and there is nothing
   in the assembler source to check. This is the most dangerous output there is,
   because its symptom is "everything is fine". Same family: `grep -c` on a file
   that does not exist gives empty output indistinguishable from "0 hits", and a
   quoted glob (`"../影片/LXX-*.html"`) is never expanded by the shell at all.
3. **Do not parse the syntax yourself.** Any check that touches code structure
   (argument counts, call sites, string contents) goes through an AST, or strips
   string literals first. Measured cost: the arity check counted commas without
   stripping strings, read the commas inside
   `note("d = ( 0.50 , 0.25 , 0 )",640,266,"sm")` as argument separators, and
   counted 7 arguments.
4. **Thresholds are read from the measurement inventory, never hard-coded, and
   the measurement environment must be declared.** Measured cost: the first
   version of the layout thresholds was measured in a 652×367 preview panel,
   while the caption band is in vh against the viewport and had been blown up to
   58%; that turned the safe zone 300–470 into a danger zone and flagged 67 of
   69 shots — **the threshold itself was inverted**. The report must open by
   printing "measurement environment: 1440×900, final-state mode". Related:
   **the fixer and the checker must share one threshold constant** (the first
   checker used a fixed 285 while the fixer placed at 195+10, and the mismatch
   reported 18 shots of false overlap).

**All green and almost all red are both reasons to suspect the checker first.**
One run came back all green and the files turned out to be wrong; one came back
67/69 and the threshold turned out to be wrong. When the proportion looks
anomalous, check the checker before you check the content.

**Uniform failure semantics**: every tool that runs before the film ships
(assemble, lint_film, audit_layout, shot_probe) exits 1 when there is a problem
and 0 when there is not, and the pipeline chains them with `&&`. Right now
`assemble_L01.py` returns 0 whether a KP is missing or a beat is missing — it
prints one warning and ships the film anyway — while `audit_layout.py` returns 1
on any problem. Two tools with opposite failure semantics, and nobody dares
chain them into a pipeline.

### Step 5 — Pre-delivery self-check (tiered: reach the highest tier you can, and disclose which tier you stopped at)

The first thing a self-check does is not render, it is **measure the
environment**. Run this probe on the target page and write both numbers into the
delivery note:

```js
({hidden: document.hidden,
  rafTicks: await new Promise(r=>{let n=0;setTimeout(()=>r(n),700);
    (function f(){n++;requestAnimationFrame(f);})();})})
```

Measured in this project: `document.hidden=true`, and rAF fired **0** times in
700 ms (a plain d3 control probe that never touches project code is just as
dead). No amount of effort gets around this; fall back.

- **L0 look at the frames** — the only complete tier, and only when rAF works:
  go shot by shot, watching the animation timing and the cuts between shots.
- **L1 DOM assertions** — run when rAF is unavailable but the DOM is readable.
  Every property that lives in the DOM rather than in rAF is checkable here:
  `setEq` must produce an `mjx-container`; `#eqBox.textContent` contains no
  backslash; decorative primitives that were deleted must genuinely be gone;
  uncaught console errors must total 0 across a per-shot `window.__go(i,true)`.
- **L2 geometry audit** — export `tag/class/fill/fontSize/getBoundingClientRect()`
  for every node in every shot's final state as JSON, then run the layout
  clause's out-of-bounds and intersection checks. The auditor passes its own
  two-way gold-sample self-test first.
- **L3 force the final state** — geometry has to be collected in the final
  state. This engine's `go()` sets `FAST=true` while replaying the preceding
  shots, but enters the **current shot** with `FAST=false`, so without a patch
  you are measuring the opening frame. See the four patches in
  `theater/src/shot_probe.js`.

**Disclosure obligation (when L0 is out of reach, write this verbatim; do not
omit it):**

> Animation timing has not been visually verified (rAF is unavailable in this
> environment; measured 0 ticks in 700 ms). L1 DOM assertions and the L2
> geometry audit are complete, covering N shots. The following M items can only
> be judged by eye, and are handed to you as a checklist: <checklist>.

**Only three and a half things genuinely need eyes**; everything else belongs to
L1/L2: (1) graphical semantics — whether a backup diagram actually looks like
backing up; (2) how the easing feels; (3) real contrast after glow/shadow
compositing; (4) the half one: how the composition sits (a shifted centre of
mass can be computed, "looks cluttered" cannot). These three and a half **do not
block delivery**, but they must be handed over explicitly, never skipped by
default.

**L1/L2 are what cannot be delegated** (they are mechanical; skipping them is
not doing them, and reporting "it should be fine" is the same as not doing
them). **L0 is what must be delegated** (if you cannot see it, hand it off).
**Writing up something you could not look at as if you had looked at it is the
one failure this skill does not accept.**

Then walk the review rubric item by item. Never report a delivery complete while
a known item is failing.
## Primitive contract

**Engine side: every primitive must throw when the argument count does not equal
the parameter count. No silent discarding.**

```js
function arrow(x1,y1,x2,y2,cls,label){
  if (arguments.length !== 6) throw new Error(`arrow expects 6 args, got ${arguments.length}`);
  ...
}
```

**Checking side: verify every call site with an AST.** Compare
`CallExpression.arguments.length` against the parameter count. **Do not count
commas.**

Measured cost: `arrow` declares 6 parameters, 10 call sites passed 7, and the
seventh was **silently discarded with no error** — the author believed an effect
had been requested that was in fact never rendered. `node --check` does not
catch this class of problem; it only checks syntax. Counting commas does not
catch it either: `note("d = ( 0.50 , 0.25 , 0 )",640,266,"sm")` counts as 7
arguments.

**Passing extra arguments is not harmless.** It is the one mechanically
catchable member of the whole family of defects where the author's intent and
what is on screen disagree — a family visual review never finds, because you
cannot see the thing that should have been there and was not — so letting it
through means giving up on the family.

**The second clause of the same principle: coordinates have exactly one source.**
Every primitive that returns a coordinate transform must have its return value
caught and used; inside one shot, nothing may re-derive those coordinates with
an arithmetic expression. Measured cost (live, not historical): KP2 shot4 threw
away `errbar`'s return value and worked out the true-μ reference line by hand as
`170+280-v/1.25*280`; the constants do not line up at all with the
`y0=177.6 / h=266.5 / ymin=-0.1` that errbar actually uses, and the ymin offset
is missing altogether: `Y(0.60)=294.86` drawn at 315.60, `Y(0.50)=316.18` drawn
at 338.00, **21.8 px too low, while the whole confidence interval on arm A is
4.26 px tall** — the picture says "A's estimate is clearly off the true value"
while the caption says "A's interval has contracted to around 0.50". Of the 14
calls to primitives of this kind across the film, only 5 caught the return
value. This error is syntactically valid, leaves a clean console, lands inside
the safe layout band, and produces a figure that looks perfectly reasonable; no
existing check finds it.

## Engineering discipline

**Regexes and strings containing backslashes always go into a `.js` / `.py` file
and run from there. Writing them straight into a shell heredoc, a `-c` argument,
or a pair of quotes is forbidden.**

Measured cost: the same backslash bug landed **seven times** (`\g`→`g`, `\r`→a
carriage return, `\+` read as a literal plus, `\{1,}` read as literal text),
every time from putting a backslash into a regex or a string inside a shell
heredoc. None of the seven was a failure to understand regex; the escaping
passed through two interpreters (shell → target language) and only one layer of
it was written. The signature of this mistake is "this time I'll remember it",
so the fix cannot be "be more careful" — it can only be **deleting that
interpreter**: in a file, a backslash is interpreted once, by the target
language; when you need a literal backslash, build it explicitly with
`BS = chr(92)`.

Corollary: **the check scripts are themselves part of the deliverable** — commit
them, reuse them, run them through `--selftest`. A throwaway shell one-liner is
not a check.

## Review rubric

**Explanation quality**
- [ ] The wrong model is named early and refuted explicitly later. An
      explanation that never collides with what the viewer already believes
      feels clear and changes little.
- [ ] Motivation lands in the first 30 seconds / first look.
- [ ] Jargon is explained; the assumed background is stated.
- [ ] One aha per episode. (Mechanically checkable: the THE AHA row of
      the spec sheet is a single non-empty line; the number of shots flagged
      as the aha for a given knowledge point == 1, and that shot contains a
      primitive call rather than text alone.)

**Cognitive load**
- [ ] Nothing on screen is decorative.
- [ ] Every referent needed for a comparison is still visible when the
      comparison is asked for.
- [ ] Labels sit next to their objects.
- [ ] Narration is not duplicated as on-screen sentences.
- [ ] Each segment is one idea; video segments are under six minutes.

**Attention routing**

- [ ] The key element is marked in the shot where it matters, using the
      **first workable** option in this order: **dim the rest → spread
      colour → a one-shot pulse (≤600 ms, iterations=1) → a plain
      colour/opacity change → a static mark (arrow, box, underline) → a
      change of position**. If position does not have to move, it never moves.
- [ ] **Nothing on screen moves without terminating.** Infinite loops,
      pulsing rings, breathing circles, marching dashes, dots pacing back and
      forth — all banned. Check: grep `infinite`, `alternate`, any
      `animation-iteration-count` whose value is not 1, and `setInterval`
      with no `clearInterval`; every count must be 0. And for every
      animation, the first frame must not equal the last frame.
- [ ] **What separates decoration from a cue is three mechanically checkable
      properties, not the name of the primitive**: `iterations === 1`,
      `durationMs <= 600`, and a non-empty `cue` field in the brief
      (format: `cue: <which object it points at> / <which line of narration lands here>`).
      Miss any one of the three and it is decoration — delete it. All three
      present, fired once, and it is a cue — allowed, and required.
- [ ] Exactly one visual focus per shot. At most one cue call.
- [ ] The cue points at what matters, not at whatever happens to be moving.
      Check: the index/colour named in the `watch` sentence is the same
      index/colour that this shot's `cls()` gives the distinguishing class to.
- [ ] One driver per shot, and everything else on screen is a pure function
      of it. Two independent timelines = a violation; `drawFn` never reads the
      clock.

**Delete the old sentence** "cued *dynamically* inside animation — a static
colour change is too weak to win against motion". It points the wrong way: it
installs motion as the default instrument of attention routing and explicitly
disparages static colour change, which collides head-on with "if a highlight
will do, do not move anything" — and since the general skill is the senior
document, the contradiction was read as a licence. The reasoning has a second
hole: static colour is "too weak" only when there is **already competing
motion** on screen, and the right conclusion is to delete the competing
motion, not to add a stronger one. Followed literally it produced pulsing
rings, breathing circles, marching dashes and little dots pacing back and
forth, and the verdict it earned was "my eyes are bleeding".

**But the overcorrection in the other direction is just as real, and has to be
blocked at the same time.** Fixing I2 deleted 8 primitives from the engine
(ping/breathe/bob/glow/walker/sweepMark/loopArrows/flow) when the correct
invariant was already written one row above in the same table ("delete any
animation whose first frame equals its last frame") — a permanent ban at the
level of the primitive is surplus stacked on top of the real rule, and it
threw out the **second largest** effect in the evidence base along with it:
signalling, retention g+=0.53 (95% CI 0.42–0.64) and transfer g+=0.33
(0.22–0.43), clearly larger than animating at all (d=0.37 / g=0.226).
Convicting by the name of a primitive also drives the behaviour underground:
the next time someone needs a one-shot cue, they will inline it inside
`drawFn`, where grep will never find it again.

So: **the ban lives on "does not terminate + carries no cue", not on the names
of primitives**; the cue primitives that fire once, run ≤600 ms and carry a
cue (`dimOthers` / `spreadColor` / `pulseOnce`) should be restored. **Looping
behaviour is never implemented inline inside `drawFn`** — anything that has to
repeat goes through a named primitive that declares its `iterations`.

**Representation linking**
- [ ] When two representations are shown (equation and picture, geometry and
      algebra), they are on screen together and the correspondence is made
      explicit by shared colour, shared labels, or an animated mapping.

**Legibility**
- [ ] **Layout (all of it numeric, all of it measured in the real
      viewport)**: in every shot, the bounding box of every primitive sits
      entirely inside that shot's available zone, and every pair of bounding
      boxes has an **intersection area of 0**.

  The available zone is fixed by **measuring the engine** — not estimated from
  a design mock, and not measured in a scaled preview panel. Measured on this
  engine at 1440×900:
  - Formula band, `setEq(...,"top")`: two lines y=51–283, one line y=90–189
  - Formula **centred** (no second argument — this is the **default
    placement**): one line y≈333–387, two lines 306–414, three lines 279–441
  - `flip(...)`: always centred, takes no pos, judged every time against the
    worst case, the three-line band (270–450)
  - Free canvas: y=290–470, horizontally x=40–1240
  - Caption band (narration shown by default): y=480–676

  Criterion: the bounding boxes of `note()` and of hand-drawn primitives fall
  entirely inside the free canvas; **y≥480 is banned outright, no
  exceptions**; the top edge moves up to y=195 only for a shot already
  confirmed to carry a one-line top formula.

  Three branches the previous version missed, each one a real miss found by
  measurement:
  1. **A formula has three placements and all three get judged.** The previous
     version recognised only `setEq(<literal>,"top")`, while centred is the
     default — a centred two-line formula occupies y=306–414, squarely inside
     the 290–470 that had been declared safe. KP7 shot5 is "centred flip +
     note@395 + note@433", and the audit reported 0 problems.
  2. **The horizontal axis gets checked.** The previous version did not check a
     single byte of it. Getting away with it this time (smallest horizontal
     margin 132 px) was luck, not a system. `note` is SVG text and does not
     wrap; whatever runs past the edge is **silently clipped** by the SVG
     root's `overflow:hidden`, with no error. Under default parameters the
     overflow points can simply be computed: matrix defaults to cw=80, so
     cols≥17 overflows; gridworld/sweepGrid default to cs=88, so cols≥15
     overflows; lamps defaults to gap=210, so n≥7 spills off the right and n≥8
     off the left; backup's compound spread×branch expansion is unbounded
     outright.
  3. **The top edge gets checked too.** The previous version had a lower bound
     and the formula band, and no check for `y<40`.

  Check: in a real 1440×900 viewport, in final-state mode, read
  `getBoundingClientRect()` for every text and graphics node, and emit two
  lists per shot — out-of-bounds items and intersecting pairs. **The report
  gives numbers shot by shot; "pass" on its own is not a report.** The static
  estimator (`audit_layout.py`) is a **coarse filter, not a verdict**: it
  checks y only and guesses formula height from keywords, so it cannot see
  horizontal overlap at the same y. If it raises an alarm there is certainly a
  problem; if it passes, that does not mean there isn't one.

  Why this clause has to carry numbers: the previous version read "Every frame
  is collision-free; nothing overlaps that should not", `should not` was left
  for the executor to define, and so it was obeyed in full while 67 of 69
  shots had layout problems — the author had treated all of 1280×720 as
  available from the start. **A collision clause without numbers is not a
  clause.** And non-negotiable 3 in Core stance had already named it: "Layout
  collisions are the single most common failure of generated animation" — the
  skill named its own leading failure mode and put zero instrumentation on it.
- [ ] **On-canvas text has a numeric budget, and the budget lives on the
      smallest channel.** Every text channel gets a word budget in this skill
      except the one the author reaches for most, and that omission has a
      measured cost: with budgets on the narration, the summary card and the
      quiz card but **none on the canvas**, on-canvas text drifted from a
      median of 90 characters per shot in the first film to 121 in the second
      and 141 in the third, and **166 of 173 shots** ended up over what the
      viewer could take in. The reviewer's words: the information on one slide
      is too dense for a brain to accept at once.

  The mechanism is not "too many words" in the abstract — it is **prose placed
  in the smallest type on the page**. Measure the channels before assigning
  text to them. On this engine:

  | Channel | Type size | Parses markup? |
  |---|---|---|
  | `note()` → `.slbl` | **14 px fixed, monospace** — the smallest on the page | **none at all** (SVG `.text()`) |
  | `setCap(h)` → `#cap` | `clamp(13.5px, 1.56vw, 22px)`, 84ch wide | innerHTML, with colour tags |
  | `setBig(v,s)` → `#big` | `clamp(30px, 5.6vw, 82px)` | innerHTML |
  | `setEq(h,pos)` → `#eqBox` | `clamp(16px, 2.5vw, 36px)` | MathJax |

  The division of labour follows from that table, and violating it blocks:
  - `note()` **labels objects only** — a short tag anchored to a drawn thing,
    meaningless once that thing is removed. No free-standing sentences, no
    argument, no caveats, no disclosures.
  - The caption carries **this shot's conclusion**, one sentence.
  - The big-display channel carries **one large assertion** — the natural home
    for the beat that states the wrong model.
  - The narration carries **the whole argument**.

  Budget, mechanically checked, counting only the `note()` calls the author
  writes (labels a primitive generates internally are anchored to geometry and
  do not count): **≤3 lines, ≤20 characters per line, ≤50 characters total.**
  A shot that cannot hold its content **splits into two shots** — under
  keyboard advance a new shot is free, and a denser one is not. Same evidence
  as the narration budget: the reversal in Leahy & Sweller (2011) is answered
  by shorter segments, never by denser ones.

  A second, separately measured trap on the same channel: **`note()` parses no
  markup whatsoever.** It is `gN.append("text")....text(t)` — an SVG text
  node, blind to Markdown and to HTML alike. Emphasis written as `**…**`
  inside `note()` rendered as **literal asterisks**, 96 of them across two
  films, and they were the first thing the reviewer saw in a screenshot; the
  same is true of markup inside `\text{…}` in a formula. Meanwhile the caption
  and the narration go through `innerHTML`, where the very same characters
  behave as intended. **One string, two channels, opposite behaviour.** On the
  canvas the only way to emphasise is to split the phrase onto its own short
  line and give it a semantic colour.
- [ ] **Font sizes come from the engine's existing closed set, and not one new
      step is added.** Hierarchy is carried by colour and position, not by
      size.

  This engine's closed set: `.axlbl` 13px / `.slbl` 14px / `.celltx` 15px —
  three steps that are almost one step, and that is deliberate.

  Check: diff the stylesheet against the content, and the count of new
  `font-size` declarations must be 0; grep for derived classes (`.slbl.big`,
  `.slbl.sm` and the like) and the count must be 0; after rendering, the
  deduplicated `getComputedStyle().fontSize` over every SVG `<text>` in the
  film must be ⊆ {13px,14px,15px}, and a fourth value is a BLOCK.

- [ ] **The minimum viewing size has a number.** The smallest intended viewing
      width is 1100 px (half a laptop screen); the canvas viewBox is 1280
      wide, so the scale factor is 0.859 and `.axlbl` 13px renders at 11.2 CSS
      px. The floor is 11 px: any SVG text rendering below 11 px at a width of
      1100 px is a BLOCK. To make a label stand out, change its colour or its
      position, never its size.

**Why not "legible at the minimum viewing size"**: that clause measures whether
something is big enough, and 19px is more legible than 14px — so it **actively
approves** an invented font size instead of stopping it. The real failure mode
runs orthogonal to it: a new size step gets invented and the hierarchy breaks.
The user's feedback was "it startles me every time it turns up"; across the 19
usable films in the ML set, font size never changed and hierarchy rode on
colour alone.

**The same fix deletes two compatibility aliases along with it.** Line 45 of
`build_common.py` reads `.slbl.ink{fill:var(--ink)} .slbl.sm{fill:var(--dim)} .slbl.big{fill:var(--ink)}`,
which has **the same specificity** as the colour classes (0,2,0 for both) and
is written after them (`engine()` inserts RL_CSS just before `</style>`, hence
after every rule in eng.txt), so it silently eats the colour: `bars` line 187
concatenates `cls + " sm"` and `errbar` line 303 concatenates `cl + " sm"` —
the semantic colour asked for by the bar-value labels in all 11 `bars` calls in
the film and by the tags in all 4 `errbar` calls is flattened to `--dim`. The
route I1 laid down, hierarchy on colour alone, was gutted from the inside by an
alias kept for compatibility with I1 — and a dim grey label on a dark ground
looks exactly like a normal label, so nobody reported it. Delete the aliases;
in the same pass drop the `sm` from those two concatenations and pass the
colour class directly, and where a bare `sm` was passed (gridworld 207, bars
185, lamps 320) pass an empty string instead (`.slbl`'s base colour is already
`--dim`, so nothing changes).
- [ ] Colour is perceptually uniform and colour-vision-deficiency safe; meaning
      is never carried by colour alone.
- [ ] No rainbow / jet colour map, no red-green pairing.

**Engagement**
- [ ] At least one generative prompt where the learner produces something.

**If the medium was locked to animation**
- [ ] The archetype is named (build / sweep / transformation) and not mixed.
- [ ] The final frame stands alone as a figure, and has been exported as one.
- [ ] A parameter sweep holds at named values and leaves a trace.

## Design-time questions (not delivery checkboxes)

These questions have no criterion, so they **must not appear on the review rubric** — mixing unverifiable items into a checklist dilutes what a tick means, from "I verified this" down to "I read this", and the authority of the verifiable items falls with it. Ask them at Step 1 and Step 3, then move on:

- What does this give the reader that the first search result cannot?
- Is there something memorable — an image, a reframing, a surprise?
- Is the aha the thing the visual actually emphasises?

Four items removed from the rubric:
- "It offers something the reader could not get from the first search result" → moved into this section
- "There is something memorable — an image, a reframing, a surprise" → moved into this section
- "The learner is not left to infer the link. Most of them will not." → **deleted outright**: it is the *reason* behind the representation-linking item above it, not a criterion, and it counted that item twice on the list
- "There is one clear aha, and it is the thing the visual emphasises" → **split**: "one aha only" stays on the rubric (mechanically checkable — THE AHA is a single non-empty line on the spec sheet; the number of shots flagged as the aha per knowledge point == 1, and that shot contains a primitive call rather than text alone); "and it is the thing the visual emphasises" moves into this section

**Why this one comes last and still has to be done**: 13 of the rubric's 23 items were class C — pure aspiration — 57% of the list. The real cost is not that those items are useless in themselves; it is that they sat **on the same sheet of paper** as mechanically checkable clauses like "count of non-terminating animations = 0". This project's §6 checklist was ticked item by item while I1/I3/I4 all went through — by then the act of ticking carried no verification meaning at all. Clearing the list once is what leaves the new clauses, the ones with numbers in them, some authority to spend.

## Reference files

| File | Read when |
|---|---|
| `evidence.md` | You need the basis for a rule, you are arguing a design choice with the user, or you are writing up the method. Holds the conclusions, the numbers, and the sources. |
| `explainer-arc.md` | The deliverable is a video about one knowledge point, or one episode of a series. **Read it before you storyboard.** |
| `theater/src/lint_film.py` | Step 5, level L1, every time. 8 mechanical checks; every comment on them is the incident record of a real failure. |
| `theater/src/audit_layout.py` | Step 5, the coarse L2 screen, every time. Every threshold comes from measurement at 1440×900. **It is a coarse screen, not a criterion.** |
| `theater/src/shot_probe.js` | Step 5, levels L2/L3, every time. Exports DOM geometry shot by shot as JSON; it produces diffable numbers, not screenshots. |

**Meta-clause: at the start of Step 5, verify every path in this table one by one with `ls` / `os.path.exists`; if any single one is missing, Step 5 fails immediately, names the missing file, and does not continue.** This covers **every skill document**, not just this table — grep the prose for every reference prefixed `references/`, `assets/`, or `scripts/` and reconcile it against this table at the same time. This is the cheapest mechanical check available (one command), and the current failure rate on it is 100%.

**In the previous version all 6 paths in this table were wrong, 6 rows out of 6**, and the fixes fall into three kinds; neither "write the missing files" across the board nor "delete the table" across the board is allowed:
1. **Wrong path, file exists** → repoint it. `references/evidence.md` and `references/explainer-arc.md` actually sit at the `skills/` root (update the references at the end of Core stance and in Step 3 to match). `evidence.md` carries the same typo at its own line 61 (`references/explainer-arc.md`), which says dangling references are not one file's accident but a systematic habit across this document set.
2. **Belongs to a medium this package does not cover** → delete the row and shrink Scope to match. The three rows `references/manim.md`, `references/static-figures.md`, and `assets/scene_template.py` are deleted.
3. **The only tool a mandatory step has** → **actually write it; never edit the prose to make a mandatory step's tool disappear.** But change what it does: what gets written is not a frame grabber (rAF never ticks, so there are no frames to grab) — it is `shot_probe.py`.

**The cost of a dead link is not "one document went unread".** Step 4 routed **the only build path** to `manim.md` / `static-figures.md`, and closed with "Start from `assets/scene_template.py`; it encodes the layout budget, the permanent-region convention, and the colour rules" — that sentence promises exactly the three things this project was missing most, and the file does not exist. So at the point where the work actually starts, the executor had nowhere to go and invented rules instead: two invented font sizes (`.slbl.big` 19px / `.slbl.sm` 11.5px) and an animation principle pointing the opposite way ("animation carries motion, not information"). **Price a dead link at that magnitude, not as document hygiene.**

**Also move `skills/teaching-viz.skill` (a zip of SKILL.md) out of the repository.** Kept alongside SKILL.md it drifts silently and no reader can tell which copy is the real one — the same breeding ground that produced the dangling references. Build the package at distribution time, not before.

## Scope

This skill's **content layer** — the Step 1 brief, the Step 2 medium gate, Step 3 segmentation and storyboarding, the six beats and spec sheet in explainer-arc, and the Explanation quality / Cognitive load / attention-guidance / Representation linking blocks of the review rubric — is medium-independent and applies to any visualisation, static or animated.

This skill's **build layer ships no code template for any medium**. When the medium and the engine are given, the build spec comes out of the Step 0 engine measurement inventory; that inventory *is* this project's `manim.md`, and without it there is no build layer.

No interactives, no voiceover. When the gate points at an interactive, say so out loud and deliver the parameter sweep plus a summary frame as the closest substitute; do not quietly hand over something weaker.

**The previous version declared "Covers Manim animation and static figures", while this project's medium is a hand-built SVG/HTML + d3 engine — formally outside the declared scope altogether. The skill was applied wholesale anyway, and Steps 4–5 hard-routed to Manim-only files and Manim-only tools. This is upstream of I12: the problem is not "the files in the table were never written", it is "the files in the table belong to a different medium".**

**Step 4 — Build (rewritten):** The build spec is decided by the medium. When both the medium and the engine are given, the Step 0 engine measurement inventory *is* the spec for this step — stop looking for a generic template. This package contains no Manim or matplotlib code template; if you work in one of those environments, build the template yourself first and treat it as a Step 0 product.

### Three archetypes become four

**4. Small-multiples strip** — the same figure redrawn side by side at three to five **named parameter values**, all visible at once, **fully static**. Requirements: every panel shares axis ranges and colour semantics; every panel carries its named value along the top; exactly one thing changes between panels.

**Reach for it first when** the claim is "a process that is understood as discrete steps" — value iteration at k=1,2,3, policy improvement round by round, n-step returns at n=1,2,∞. Basis [A: the congruence principle, Tversky, Morrison & Bétrancourt 2002]: many continuous events are conceptually a sequence of discrete steps, and **a continuous sweep is the worse match for them**. `evidence.md` §2 says outright that the small-multiples strip is a **first-class output of this method, not a consolation prize** — and the previous version's three files never mentioned it once.

**Extra reason, specific to this project**: it is fully static, so in an environment where rAF is dead it is the **only multi-state narrative form that can be verified mechanically end to end** — every panel is rendered at t=0, so the layout, overflow and greyscale checks all run. It also gives "failed all four gates" somewhere dignified to land, so a static output stops reading as a failure. **If a strip can make it clear, do not use a sweep.**

### When the medium has no audio track

(a) There is no voiceover pointing at things in sync, so **"what to look at" has to be written into the text** — it cannot ride on timing.
(b) The reader can pause, so a single frame may carry more, but **one shot still changes exactly one thing**.
(c) **"I want it to feel alive" is not "I want motion"** — the answer is a rhythm of advance (one change per shot, discrete beats, a reveal on every beat), not something spinning on screen. **This is the one that gets broken again and again.**

**On-canvas text and narration text divide the work differently; the reason changes with the medium, the conclusion does not:**
- With an audio track: do not print the voiceover as full on-screen sentences saying the same thing (modality/redundancy effect).
- **With no audio track (the narration is itself on-screen text)**: the caption band carries the full sentences and **the canvas holds short labels only**. Criterion: no text node inside the free canvas may repeat that shot's narration at sentence level (longest common substring ≥12 Chinese characters = WARN, ≥20 = BLOCK).
- **Never use canvas coordinates to place content that belongs in the narration text.**

The previous version copied "Do not put the narration on screen as text as well" verbatim into a project with **no audio track**. Its evidence base is the modality/redundancy effect — an audio track plus captions saying the same thing — whereas here the narration *is* on-screen text and the caption band *is* the "narration". Read literally, an executor either reaches the absurd conclusion that the narration may not go on screen, or decides the clause does not apply and throws the whole thing away. **A clause with the wrong reason attached gets ignored, correctly.** I5 is downstream of this ambiguity: no clause ever drew the boundary between on-canvas text and the caption band. (PROJECT §7 had already spotted that "he has a voiceover pointing along in sync, we do not", while §3 still copied this audio-premised rule across unchanged — the diagnosis was right and the clause never caught up.)