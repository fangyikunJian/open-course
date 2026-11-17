# Evidence base

Why each rule in SKILL.md exists. Organised as: finding → what it implies for
design. Read the section you need; the table of contents is the fast path.

1. Does animation actually help?
1b. The biggest effect here is not animation — it is refuting the wrong model
2. When animation is the right medium (congruence, apprehension)
3. Transience and working memory
4. Segmenting, pacing and learner control
5. Cueing and signalling
6. What to cut, and where to put words
7. Concrete before abstract
8. Linking two representations
9. Prior knowledge cuts both ways
10. Engagement: passive watching is the weak mode
11. Video production findings
12. Figure and colour craft
13. What good exposition looks like (practitioner criteria)
14. What AI systems get wrong at this task
15. Sources

---

## 1. Does animation actually help?

Two meta-analyses set the baseline. Höffler & Leutner (2007), 26 studies and 76
pairwise comparisons, found a small-to-medium overall advantage for instructional
animation over static pictures: d = 0.37 (95% CI 0.25–0.49). The advantage was
larger when the animation was *representational* rather than decorational
(d = 0.40), larger still for highly realistic/video material (d = 0.76), and
largest for procedural-motor knowledge (d = 1.06). Berney & Bétrancourt (2016),
61 studies, 140 comparisons, >7000 participants, found a smaller effect:
g = 0.226 (95% CI 0.12–0.33).

**Implication.** Animation is a modest, conditional win, not a default. The
conditions that carry the effect — representational motion, procedural content —
are exactly the conditions the medium gate tests for. Decorative motion is
outside the evidence entirely.

## 1b. The biggest effect here is not animation — it is refuting the wrong model

Muller, Bewes, Sharma & Reimann (2008) randomly assigned 364 first-year physics
students to four online multimedia treatments on Newton's laws: a concise
lecture-style exposition; the same plus extra interesting material; a
*refutation* version that stated common misconceptions explicitly and refuted
them; and a *dialogue* between a student and a tutor covering the same ground.
Measured on conceptual-inventory items, refutation beat plain exposition with
an effect size of about 0.79, and dialogue about 0.83. Students with low prior
knowledge gained most, and students with high prior knowledge were not
disadvantaged.

Put that next to §1: the misconception effect is roughly twice the size of the
animation effect. Related work from the same author attributes the mechanism to
mental effort — the clean exposition feels clearer and costs less, and that is
precisely why it fails to displace the existing model.

**Implication.** The brief has a Misconception field, and it is not optional
decoration. For video work the misconception gets its own beat near the start
and a matching refutation beat near the end (see
`explainer-arc.md`). If a piece cannot name the wrong model it is
arguing against, expect it to feel good and change nothing.

## 2. When animation is the right medium

Tversky, Morrison & Bétrancourt (2002) reviewed the comparisons and found the
case for animation unconvincing: where animation appeared to win, the animated
condition usually carried extra information or extra interactivity that the
static condition lacked. They proposed two principles that a graphic must
satisfy:

- **Congruence** — the structure and content of the graphic should correspond to
  the structure and content of the idea. Change over time in the picture should
  map onto change over time, sequence, or causal flow in the concept.
- **Apprehension** — the graphic must be accurately perceivable and
  comprehensible. Animations frequently violate this: too fast, too much at
  once. And many continuous events are conceptualised as sequences of discrete
  steps, so a continuous sweep can be a worse match than discrete stills.

They note that judicious interactivity can rescue both problems.

**Implication.** Tests A and B of the medium gate. Also the reason a
"small multiples" strip is a first-class output of this skill and not a
consolation prize: for a continuous process understood as discrete states, the
strip is the *congruent* representation.

## 3. Transience and working memory

Cognitive load theory adds a mechanism. Information is *transient* when elements
disappear and are replaced by new ones; if old and new elements interact, the old
must be held in working memory while the new are processed. Wong, Leahy, Marcus &
Sweller (2012) point out that educational technology routinely converts permanent
information into transient information — replacing a series of static frames with
an animation of the same motion does exactly this — and that the resulting load
can be overwhelming. Their remedy is shorter segments: a short segment imposes
less load, which lets the natural advantages of animation and narration show up.

The same effect explains a limit on the modality principle: Leahy & Sweller
(2011) found the usual narration-beats-text advantage with short spoken
explanations, and a *reversal* with long ones — extended speech is itself
transient information.

**Implication.** Test C of the gate. Anything needed for a later comparison
stays permanently on screen. And: narrate in short bursts, not paragraphs.

## 4. Segmenting, pacing and learner control

Mayer's segmenting principle: people learn better from a lesson broken into
learner-controlled segments than from a continuous unit. Pre-training: people
learn better when they already know the names and characteristics of the key
concepts before the process is explained.

Learner control is not automatic, though. Studies on pausing and scrollbars find
that learners need explicit guidance on *when* to pause; a pause button alone
does less than expected.

**Implication.** Segment by idea. Build the stopping points into the artefact
rather than hoping the viewer invents them — an explicit "pause here and predict"
does the work a bare pause button does not. Pre-train every symbol.

## 5. Cueing and signalling

Signalling — adding cues that highlight the essential material or its
organisation — is one of the better-supported principles. A meta-analysis of
signalling reports retention g+ = 0.53 (95% CI 0.42–0.64) and transfer
g+ = 0.33 (95% CI 0.22–0.43), with reduced cognitive load and more fixations on
the relevant regions.

But cueing *inside animation* is fussier than cueing in static graphics.
Reviews (de Koning et al. 2009 and later eye-tracking work) find mixed results,
with a leading explanation that classic static-style signals — a colour change,
a sudden appearance, a luminance contrast — are simply too weak to capture
attention against a moving background. Dynamic signals, such as a spreading
colour cue, do better. Cueing also works better when paired with
self-explanation prompts than alone.

**Implication.** Cue, but cue dynamically inside animation: motion, zoom,
spreading colour, dimming everything else. Do not assume a red highlight will
be noticed while other things move. Pair the cue with a question.

## 6. What to cut, and where to put words

Mayer's principles for managing extraneous load, all with experimental support:

- **Coherence** — exclude extraneous words, pictures and sounds. Interesting
  but irrelevant detail measurably hurts. Quantitative detail can damage
  qualitative understanding (Mayer & Jackson 2005).
- **Redundancy** — graphics + narration beats graphics + narration + on-screen
  text duplicating the narration.
- **Spatial contiguity** — printed words next to the part of the graphic they
  describe, not in a distant legend.
- **Temporal contiguity** — corresponding words and pictures at the same time.
- **Modality** — present words as speech rather than on-screen text (subject to
  the length limit in §3).

**Implication.** The storyboard's three columns, and the "nothing decorative"
rubric line. Note that captions for accessibility are a different thing from
redundant on-screen prose; the redundancy finding is about duplicating the
explanation, not about subtitles for access.

## 7. Concrete before abstract

Concreteness fading: begin with a concrete instantiation, pass through an
intermediate form that keeps the correspondence but strips extraneous detail,
and end at the abstract symbol. McNeil & Fyfe (2012) taught undergraduates
modular arithmetic in concrete, abstract, or faded conditions; the faded group
had the best transfer immediately, at one week, and at three weeks. The
systematic review (Fyfe, McNeil, Son & Goldstone 2014) attributes the benefit to
grounding opaque symbols in well-understood objects, supplying memorable images
for when the symbols stop meaning anything, and guiding learners to strip away
the inessential.

**Implication.** The ordering rule in Step 3, and the instruction to keep the
concrete case visible while the general symbol appears.

## 8. Linking two representations

Mathematical exposition constantly shows two representations at once — an
equation and a picture, a geometric margin and a dual formulation. Ainsworth's
DeFT framework warns that learners very often fail to translate between them.
Yerushalmy (1991), cited there, found that after extended multi-representational
teaching about functions, only about 12% of students gave answers drawing on
both the numerical and the visual representation; most used one and ignored the
other. The framework recommends keeping representations co-present and raising
their perceived similarity, e.g. by matching labels — while noting the tension
that if the system does all the translation for the learner, the learner never
builds the link themselves.

**Implication.** The representation-linking rubric block. Shared colour for
shared quantities, matched labels, an animated mapping from one to the other,
and a prompt that makes the learner do the last step of the translation.

## 9. Prior knowledge cuts both ways

The expertise reversal effect: support that helps novices can hurt experts.
Kalyuga (2008) found the relative effectiveness of animated versus static
diagrams depends on learner prior knowledge, and segmentation shows expertise
reversal too (Spanjers et al. 2011).

**Implication.** The brief names the audience and their prior knowledge, and the
artefact states its assumed background. There is no design that is right for
everyone.

## 10. Engagement: passive watching is the weak mode

Chi & Wylie's ICAP framework orders modes of engagement Interactive >
Constructive > Active > Passive, and reports gains of roughly 8–10% with each
step up. It is consistent with the large meta-analysis of active learning in
college classrooms (Freeman et al. 2014).

**Implication.** A video is a passive artefact by default. The generative prompt
is what moves it up a rung, and it is the cheapest quality gain available.

## 11. Video production findings

Guo, Kim & Rubin (2014) analysed 6.9 million video-watching sessions across four
edX courses. Shorter videos were much more engaging — their recommendation is to
invest in pre-production planning and segment into chunks under six minutes.
Khan-style tablet drawing was more engaging than slides or code screencasts, and
high-quality recordings of classroom lectures did not transfer well to online.

**Implication.** The six-minute ceiling, and the preference for progressive
drawing over slide reveals. Note the engagement/learning distinction: this study
measures watch time and problem attempts, not learning gains. Treat it as
evidence about attention, not comprehension.

## 12. Figure and colour craft

Rougier, Droettboom & Bourne (2014), "Ten Simple Rules for Better Figures":
know your audience, identify the message, adapt the figure to the medium,
caption properly, do not trust the defaults, use colour effectively, do not
mislead, avoid chartjunk, message over beauty, and use the right tool. They note
that student audiences are a special case — the goal is to explain a concept,
so extra explanatory information may need to be *added* rather than stripped.

Crameri, Shephard & Heron (2020) document that colour maps distorting data
through uneven gradients, or unreadable under colour-vision deficiency, remain
common — rainbow-like and red-green maps especially. Perceptually uniform,
CVD-safe maps report true variation and stay readable in greyscale. Discordant
false colouring can produce visual errors of several percent of the displayed
range.

**Implication.** The legibility rubric block. Use perceptually uniform maps
(viridis and relatives, Crameri's scientific colour maps), never rainbow/jet,
never red-green as the only distinction, and always check the greyscale case.

## 13. What good exposition looks like (practitioner criteria)

The Summer of Math Exposition judges on four criteria, which make a usable
quality bar because they are about the reader's experience rather than the
author's effort:

- **Clarity** — jargon explained, goals understandable with minimal background,
  empathy for the unfamiliar reader.
- **Motivation** — within the first 30 seconds it should be clear why anyone
  should care.
- **Novelty** — offer an experience not obtainable by searching around;
  covering a common topic *better* counts.
- **Memorable** — something should survive several months, whether beauty,
  enthusiasm, or the shape of an aha.

Related practitioner advice from the same source: structure from concrete to
abstract, pick a specific topic, know which genre you are in (exposition by
someone who understands it deeply vs. discovery journalism where you learn
alongside the viewer), and avoid flashy effects that do not carry explanation.

Adjacent traditions worth knowing: explorable explanations (Victor's framing is
that the guidance must direct attention to particular phenomena, which is what
separates an explorable from a pile of widgets), and Distill's work on
interactive articles.

## 14. What AI systems get wrong at this task

TheoremExplainAgent (Ku et al., ACL 2025) generates long-form Manim explanation
videos with planning and coding agents, and ships TheoremExplainBench (240
theorems, 5 automated metrics). Two findings matter here. First, agentic
planning is essential for coherent long-form output — the plan, not the code, is
the bottleneck. Second, the remaining weakness is visual element layout: the
authors call out spatial reasoning and refinement as the open problem. Related
work (manimator) turns papers into visual explanations along the same lines.

**Implication.** Steps 1–3 of this skill exist because planning is where the
quality is. Step 5 exists because layout is where the failures are.

## 15. Sources

- Höffler, T. N. & Leutner, D. (2007). Instructional animation versus static pictures: A meta-analysis. *Learning and Instruction*, 17(6), 722–738.
- Berney, S. & Bétrancourt, M. (2016). Does animation enhance learning? A meta-analysis. *Computers & Education*, 101, 150–167.
- Tversky, B., Morrison, J. B. & Bétrancourt, M. (2002). Animation: can it facilitate? *International Journal of Human-Computer Studies*, 57(4), 247–262.
- Wong, A., Leahy, W., Marcus, N. & Sweller, J. (2012). Cognitive load theory, the transient information effect and e-learning. *Learning and Instruction*, 22(6), 449–457.
- Leahy, W. & Sweller, J. (2011). Cognitive load theory, modality of presentation and the transient information effect. *Applied Cognitive Psychology*, 25, 943–951.
- Mayer, R. E. (2021). *Multimedia Learning*, 3rd ed. Cambridge University Press. See also Mayer (2021), Evidence-based principles for how to design effective instructional videos, *Journal of Applied Research in Memory and Cognition*.
- Mayer, R. E. & Jackson, J. (2005). The case for coherence in scientific explanations. *Journal of Experimental Psychology: Applied*, 11(1), 13–18.
- de Koning, B. B., Tabbers, H. K., Rikers, R. M. J. P. & Paas, F. (2009). Towards a framework for attention cueing in instructional animations. *Educational Psychology Review*, 21(2), 113–140.
- Boucheix, J.-M. & Lowe, R. K. (2010/2013). Work on dynamic (spreading-colour) cueing in animation.
- Fyfe, E. R., McNeil, N. M., Son, J. Y. & Goldstone, R. L. (2014). Concreteness fading in mathematics and science instruction: a systematic review. *Educational Psychology Review*, 26(1), 9–25.
- McNeil, N. M. & Fyfe, E. R. (2012). "Concreteness fading" promotes transfer of mathematical knowledge. *Learning and Instruction*, 22(6), 440–448.
- Ainsworth, S. (2006). DeFT: A conceptual framework for considering learning with multiple representations. *Learning and Instruction*, 16(3), 183–198.
- Kalyuga, S. (2008). Relative effectiveness of animated and static diagrams: An effect of learner prior knowledge. *Computers in Human Behavior*, 24(3), 852–861.
- Chi, M. T. H. & Wylie, R. (2014). The ICAP framework: linking cognitive engagement to active learning outcomes. *Educational Psychologist*, 49(4), 219–243.
- Guo, P. J., Kim, J. & Rubin, R. (2014). How video production affects student engagement: an empirical study of MOOC videos. *L@S '14*.
- Rougier, N. P., Droettboom, M. & Bourne, P. E. (2014). Ten simple rules for better figures. *PLOS Computational Biology*, 10(9), e1003833.
- Crameri, F., Shephard, G. E. & Heron, P. J. (2020). The misuse of colour in science communication. *Nature Communications*, 11, 5444.
- Muller, D. A., Bewes, J., Sharma, M. D. & Reimann, P. (2008). Saying the wrong thing: improving learning with multimedia by including misconceptions. *Journal of Computer Assisted Learning*, 24(2), 144–155. See also Muller, Sharma & Reimann (2008), Raising cognitive load with linear multimedia to promote conceptual change, *Science Education*, 92(2), 278–296.
- Arcavi, A. (2003). The role of visual representations in the learning of mathematics. *Educational Studies in Mathematics*, 52(3), 215–241.
- Sanderson, G. Summer of Math Exposition announcements and results, 3blue1brown.com.
- Victor, B. (2011). Explorable Explanations. Hohman, F., Conlen, M., Heer, J. & Chau, D. H. (2020). Communicating with Interactive Articles. *Distill*.
- Ku, M. et al. (2025). TheoremExplainAgent: towards video-based multimodal explanations for LLM theorem understanding. *ACL 2025*. arXiv:2502.19400.
