# Ear Number: a three-digit description of an ear's hearing

**Nicholas Hill**, 2026. Version 1 of the code and its table.
Licence: this paper, the table `earnumber-v1.json` and the figures are
CC BY 4.0; the code is MIT (see `LICENSE` and `LICENSE-DATA.md`).

## Abstract

Ear Number describes the hearing of one ear with a number from 000 to 999.
Higher numbers mean better hearing, and the number decodes to an approximate
pure-tone audiogram. A pair of ears is written left then right, for example
`705 688 4` (the last digit is a check digit). The number has two parts: a
quality level (20 steps of 5 dB of an importance-weighted average
threshold) and one of 50 audiogram shapes learnt from 29,061 ears in four
cycles of the US National Health and Nutrition Examination Survey (NHANES),
with each ear weighted by how common hearing loss is at its age. On a test
group of ears not used to build the table, the decoded audiogram differs
from the measured one by a median of 4.5 dB (ages 6-19), 4.5 dB (20-69)
and 5.1 dB (70 and over), root mean square over 0.5-8 kHz, which is about
the repeatability of clinical audiometry. The number ranks
older people by their self-reported hearing as well as any formula tested
(Spearman 0.62 at 70+). This paper explains what the number is for, how it
was designed and derived, how to rebuild the table from the public data,
and how to use it.

## 1. What Ear Number is for

"20/20 vision" is widely understood even by people who could not say what
the two numbers mean: it is a short, memorable statement of visual acuity,
and its order is obvious. Hearing has no such everyday number. An audiogram
describes an ear well but is a chart of a dozen values, hard to remember or
quote, and clinical labels ("moderate loss") are coarse.

Ear Number aims to be:

- **Memorable and quotable**: three digits per ear, six for a person.
- **Ordered**: a higher number means better hearing, across the whole range
  from a young normal ear (999) to no usable hearing (000).
- **Decodable**: the number turns back into an approximate audiogram, so it
  carries the shape of the hearing, not only its degree.
- **General**: valid for children, adults and older people, and for any
  degree of loss.
- **Practical**: computable exactly from a clinical audiogram, and
  estimable from a short self-test such as the one in an app.
- **Open**: the method, table and code are free to reuse.

Section 5.6 compares Ear Number with two other schemes on the same ears.

Ear Number is a description of hearing thresholds. It is not a diagnosis,
does not replace a hearing assessment, and says nothing about the cause of
a hearing loss.

## 2. Definition

### 2.1 Input

Pure-tone air-conduction thresholds in dB HL for one ear at 500, 1000,
2000, 4000 and 8000 Hz (required) and 3000 and 6000 Hz (optional). A 250 Hz
value is accepted and ignored.
No response at the audiometer's limit counts as 100. Values need not be
multiples of 5 dB. The order of operations is fixed. First, each supplied
value is limited to -10 to 100 dB HL. Second, a missing 3000 or 6000 Hz
value is interpolated linearly in dB on a logarithmic frequency axis
between its neighbours. Third, the 250 Hz value is set to the 500 Hz
value, whether or not one was supplied.

The number therefore depends only on 500 to 8000 Hz. A 250 Hz threshold adds
little to speech intelligibility, the survey behind the table did not measure
it, and a loss mainly in the low pitches is better handled as a feature for a
reserved suffix letter in a later version.

### 2.2 Quality level

The importance-weighted mean threshold is

H = 0.0617 T(250) + 0.1671 T(500) + 0.2373 T(1000) + 0.2648 T(2000)
+ 0.2142 T(4000) + 0.0549 T(8000)

where the weights are the octave-band importance function for average
speech in ANSI S3.5-1997, the Speech Intelligibility Index standard (they
sum to 1). The quality level is

q = 19 - min(max(floor(H / 5), 0), 19)

so there are 20 levels, each 5 dB of H wide; level 19 is H below 5 dB HL
and level 0 is H of 95 dB HL or more. H is rounded to six decimal places
before the level is taken, so that a flat 20 dB audiogram gives exactly 20
and lands in the 20-25 dB level whatever the floating-point arithmetic.

### 2.3 Shape

The residual is the audiogram minus H at the seven shape frequencies
(500, 1000, 2000, 3000, 4000, 6000, 8000 Hz). The shape index s (0-49) is
the index of the nearest of the 50 residual curves in the table, by summed
squared difference. Shapes are numbered so that a higher index means a
higher cutoff: they are sorted by the edge frequency of the curve (where it
first rises 20 dB above its 1 kHz value; a curve with no edge counts as
highest), and shapes with equal or no edge by their mean residual over
4-8 kHz, more treble loss first. Shape 0 has the lowest cutoff and the
steepest treble loss; the last 12 shapes have no edge below 8 kHz and are
ordered by treble loss only. If two shapes are equally near, the lower
index is used.

### 2.4 The number

N = 50 q + s, written with three digits (leading zeros kept). For two ears,
left then right, with an optional check digit: `LLL RRR C` (section 2.7).
The number 000 is reserved (section 2.8).

### 2.5 Decoding

The decoded audiogram is the level centre plus the shape's residual:

T(f) = (19 - q + 0.5) x 5 + r_s(f), limited to -10..100 dB HL,

at the seven shape frequencies, with 250 Hz taken equal to 500 Hz.

### 2.6 Reading a number

The hundreds digit gives the quality in 10 dB steps of H; within each
hundred, 00-49 is the poorer of two levels and 50-99 the better; the last
part identifies the shape. Only the level ranks: numbers in the same block
of 50 (for example 905 and 940) describe equally good hearing with
different shapes, while 950 is one level better than 949.

| Number | H (dB HL) | Approximate WHO grade (for flat losses) |
|---|---|---|
| 800-999 | under 20 | normal |
| 650-799 | 20 to 35 | mild |
| 500-649 | 35 to 50 | moderate |
| 350-499 | 50 to 65 | moderately severe |
| 200-349 | 65 to 80 | severe |
| 050-199 | 80 to 95 | profound |
| 000-049 | 95 or more | complete |

WHO grades are defined on the four-frequency average of the better ear
(World Health Organization 2021); H weights the frequencies differently,
so the correspondence is exact only for flat audiograms.

What the numbers mean to people, from NHANES participants' own rating of
their hearing without a hearing aid (the block of 50 holding the lower quartile, the median and the upper
quartile of the better ear's number; section 5.3). Blocks are used
because within a block the last digits are the shape and do not rank
hearing.

| Self-report | 70 and over | 20-69 | All ages |
|---|---|---|---|
| excellent | 700-749 / 750-799 / 800-849 | 850-899 / 900-949 / 950-999 | 850-899 / 900-949 / 950-999 |
| good | 650-699 / 750-799 / 800-849 | 850-899 / 900-949 / 950-999 | 850-899 / 900-949 / 950-999 |
| a little trouble | 550-599 / 600-649 / 700-749 | 750-799 / 800-849 / 900-949 | 700-749 / 800-849 / 900-949 |
| moderate trouble | 500-549 / 550-599 / 650-699 | 650-699 / 750-799 / 850-899 | 550-599 / 700-749 / 800-849 |
| a lot of trouble | 350-399 / 450-499 / 500-549 | 450-499 / 600-649 / 750-799 | 400-449 / 500-549 / 600-649 |
| deaf | 200-249 / 250-299 / 350-399, 14 people | fewer than 10 people | 000-049 / 250-299 / 350-399, 19 people |

For people aged 70 and over in the 2017-20 cycle, the block of the better
ear's median number by what it can understand without seeing the speaker's
face: 750-799 (rates hearing excellent or good), 650-699 (a whisper across
a quiet room), 600-649 (a normal voice but not a whisper), 500-549 (a
shout but not a normal voice), 400-449 (only loud speech into the ear; 24
people) and 250-299 (not even that; 11 people). These tables use all
persons with a self-report.

People rate their hearing against what they expect for their age, so the
same rating corresponds to lower numbers in older people.

**Comparing two numbers.** Two numbers 50 or more apart are always in the
right order of H (100.0% of random pairs of test ears). Numbers 25 to 49
apart are in the right order for 93.4% of pairs. Closer than 25 apart the
order means almost nothing: 61.7% for a gap of 10 to 24 and 52.3% for a
gap of 1 to 9, where 50% is chance.

**Repeating a test.** In the simulated retest of section 3.3, the share of
ears in the population whose level is unchanged is 61%, whose level moves
one step is 38%, and whose level moves two or more steps is 1%. The
identical number comes back for 33%. A change of 100 or more in the number
can be treated as real, since it needs a move of two levels.

### 2.7 Writing a person's number

A person is written left ear, right ear, check digit: `LLL RRR C`, for
example `705 688 4`. The check digit is optional, but its use is
encouraged: it is computed with the Damm algorithm (Damm 2004) over the six
ear digits, and it catches every single mistyped digit and every swap of two
adjacent digits. It does not catch every exchange of the left and right
ears: it catches 89% of them.

A number may be entered with spaces, commas or hyphens between the parts,
or as an unbroken string. Six digits mean no check digit; seven mean the
last is the check digit. Because each ear always has exactly three digits,
this is never ambiguous. Software should reject a number whose check digit
does not match and ask for it again, never guess a correction.

An ear may carry suffix letters directly after its three digits, for
example `456E`. Suffixes are upper case (lower case input is converted),
are not included in the check digit, and use only letters that cannot be
mistaken for digits: A C E F H J K M N P R V W X Y (I, L, O, Q, D, Z, S, G,
T, B and U are excluded). Suffixes describe how a number was obtained or a
feature of the audiogram, never a medical condition. Version 1 defines two:

| Suffix | Meaning |
|---|---|
| (none) | from a calibrated audiogram of that ear |
| E | estimated by a self-test on an uncalibrated device (section 6.3) |
| N | not measured on this ear; the value is assumed (copied from the other ear, or a default chosen by the system using it) |

The other letters are reserved for later versions.

### 2.8 Deaf, missing and unmeasured ears

**000 is reserved for no hearing**: an ear with no response at every
frequency, or no ear on that side, whether from birth or from an accident.
For perceiving sound through that side the two are equivalent. 000 decodes
to no response (100 dB HL) at every frequency, and the encoder gives 000
only to such an ear: when every value, after the completion of section 2.1
is at 100 dB HL. At level 0 shape 0 is
never chosen, so no other ear receives 000.

**An ear that has not been measured** is not 000. Hearing is usually
similar in the two ears, so a fair default is to copy the measured ear and
mark the copy: if the left ear is 456 and the right was not tested, the
person is `456 456N`. In NHANES, the two ears of a person are at the same
quality level for 56% of people aged 6-19, 45% aged 20-69 and 32% aged 70
and over; within one level for 94%, 86% and 73%; and four or more levels
(20 dB) apart for 1.2%, 3.2% and 6.0%. A copied ear is therefore usually
close, but the mark matters, especially for older people.

A system that uses Ear Number may also substitute a default and mark it the
same way: `999N` to leave that ear's sound unadjusted, or `000N` to send
nothing to that side. A number with no suffix always comes from a
measurement of that ear.

## 3. How the design was reached

The design was settled by testing candidates against data rather than by
choosing constants to fit expectations. The steps that shaped it:

### 3.1 One ranking quantity first

A natural first idea gives each digit one property of the audiogram (for
example the level at 1 kHz, the cutoff frequency and the slope). Such a
number decodes reasonably, but its order is lexicographic: the first digit
outranks everything after it. An ear that is good at 1 kHz but loses all
the treble then outranks an ear slightly poorer at 1 kHz with full treble,
which is the wrong way round. A number whose order means "better hearing"
must lead with a single quality measure and use the remaining information
only to describe.

### 3.2 The quality measure

The Speech Intelligibility Index (SII) is the established measure of how
much of speech an ear can hear, but computed for conversational speech in
quiet it reaches zero at about 55 dB HL: every severe and profound ear
would share the bottom of the scale. Ear Number keeps the SII's frequency
importance weights but averages the thresholds themselves, which has no
floor and follows the audiogram smoothly to 100 dB HL.

The way of combining frequencies was chosen by a criterion independent of
the audiogram: the better ear's value should rank people as they rate
their own hearing. In NHANES participants aged 70 and over (2,207 people;
six-point self-report without a hearing aid; a bootstrap over people to
separate real differences from noise), averaging in dB with SII or with
four-frequency weights ranked best (Spearman 0.627 and 0.626). Penalising
uneven hearing (a harmonic mean of per-band values) ranked no better
(0.615 to 0.630 depending on strength, significantly worse when strong),
favouring the best bands was worse (0.584), scoring the weakest band was
worse (0.474), and the 1 kHz threshold alone was clearly worse (0.498). The
same held against a functional ladder in the 2017-20 cycle (whether the
better ear understands a whisper, a normal voice or a shout across a quiet
room, or loud speech into the ear). The result: average in dB, with no
extra penalty for shape; shape is described by the shape index instead.

### 3.3 The step size

Measurement noise in audiometry is roughly constant in dB, so equal steps
in dB use the digits efficiently (as the logMAR scale does for visual
acuity; Bailey and Lovie 1976). With a simulated retest (4 dB of
independent error per frequency plus 2 dB common to the ear, rounded to
5 dB steps), 20 levels of 5 dB moved the level by two or more steps in 2%
of ears; 40 levels moved 21% and 50 levels 31%. NHANES measures the 1 kHz threshold twice in
the same session. Over 29,023 ears with both readings valid, the standard
deviation of the difference is 3.2 dB and 2.7% differ by 10 dB or more. The
simulated retest, with 4 dB of error per frequency, is therefore cautious
for a repeat in the same session. Five dB is also the
audiometer's own step. Twenty levels leave 50 shapes per level within
1,000 numbers.

### 3.4 The shapes

Shapes learnt from data (k-means clustering of the residual curves)
decoded better than shapes defined by formula (cutoff bins by treble bins):
in the development data (ages 70+), 5.0 against 6.1 dB median error with
the same 20 x 50 grid, while ranking equally well. Other splits of the
1,000 numbers decoded slightly worse (25 x 40: 5.1 dB; 40 x 25: 5.3 dB;
50 x 20: 5.5 dB) and were less stable on retest. For comparison, earlier
candidates without the level-plus-shape structure reached 9.3 dB (one
digit each for 1 kHz level, cutoff and slope) and 9.7 dB (SII score plus a
cutoff digit).

The final build was compared with other designs, all trained on the
training half with loss weights and scored on the test group (median / 90th
percentile error in dB; share of ears over 10 dB):

| Design | Numbers | Median / 90th | Over 10 dB |
|---|---|---|---|
| 10 shapes | 200 | 6.0 / 9.5 | 8.1% |
| 20 shapes | 400 | 5.4 / 8.5 | 4.8% |
| 50 shapes (shipped) | 1000 | 4.9 / 7.5 | 2.2% |
| 100 shapes | 2000 | 4.4 / 6.8 | 1.3% |
| two-parameter formula, 10 x 5 lattice | 1000 | 5.3 / 8.6 | 4.8% |

Fifty shapes is a point of diminishing returns, not a ceiling. One hundred
shapes would give 4.4 dB at the median and 6.8 dB at the 90th percentile,
but need 2,000 numbers, which is four digits per ear. The level alone,
decoded with the typical shape of its level, gives 9.2 / 17.0 dB, so the
shape part roughly halves the error. The formula is stronger than the one
tested during development: it places each ear on a 10 x 5 lattice on the
first two principal components of the residuals. The learnt shapes still
win by a few tenths of a decibel at the median (4.9 against 5.3 dB) and
leave about half as many poorly described ears (2.2% against 4.8% over
10 dB).

### 3.5 Who the shapes are learnt from

The number is for everyone, but what it most needs to describe well is
hearing loss, and hearing loss is concentrated in later life. In NHANES the
proportion of ears with hearing loss (WHO definition: a mean of 0.5, 1, 2
and 4 kHz of 20 dB HL or worse) is about 2% in children, 9% at 40, 40% at
60 and 89% at 80. Weighting ears by the population alone would let the
large number of young normal ears decide most of the shapes; weighting age
bands equally depends on where the bands are drawn. The shapes are instead
learnt from a training population with the age profile of ears with
hearing loss: each ear counts in proportion to the number of people with
hearing loss at its age (section 4.2). Every ear, with or without loss,
still contributes at its age, so normal hearing keeps its own shapes (29 of
the 50 describe mostly normal ears).

Three weightings compared on the test ears (median / 90th percentile
error, dB; "weighted to hearing loss" counts test ears the way the chosen
weighting counts training ears):

| Training weight | 6-19 | 20-69 | 70+ | Weighted to hearing loss |
|---|---|---|---|---|
| equal per age band (6-19, 20-69, 70+) | 3.9 / 5.9 | 4.4 / 6.9 | 5.1 / 8.1 | 4.9 / 7.6 |
| US population | 3.9 / 5.9 | 4.3 / 6.9 | 5.3 / 8.2 | 4.9 / 7.6 |
| hearing loss at each age (chosen) | 4.5 / 6.7 | 4.5 / 6.8 | 5.1 / 7.8 | 4.9 / 7.5 |

By WHO grade of the ear (median error, dB):

| Training weight | under 20 | 20-34 | 35-49 | 50-64 | 65 and over |
|---|---|---|---|---|---|
| equal per age band | 4.1 | 5.4 | 5.4 | 5.3 | 4.7 |
| US population | 4.1 | 5.4 | 5.6 | 5.5 | 4.7 |
| hearing loss at each age (chosen) | 4.4 | 5.3 | 5.4 | 5.3 | 4.5 |

Weighting to hearing loss is best or equal best at every grade of loss and
for the over-70s, most clearly for the worst-described tenth of older ears
(90th percentile 7.8 dB against 8.1 and 8.2); the cost falls on normal
hearing (0.3 dB) and children (0.6 dB). The differences are tenths of a
decibel. The level step alone contributes about 1.3 dB (median error with
the exact shape and the 5 dB level). The shapes alone contribute 4.6 dB
(exact level, nearest shape; loss-weighted), and so dominate the error.
That error is much the same under the three weightings, so the choice
rests mainly on principle: the training population should be the
population the number is chiefly for, and the comparison shows that this
costs people with hearing loss nothing and gains them a little. The weighting
changes only the shapes: the quality levels are fixed 5 dB steps of H, so
a change in hearing, including within mild loss, moves the level in the
same way under any weighting.

## 4. Data and derivation

### 4.1 Source

NHANES public-use files from the National Center for Health Statistics
(NCHS), US Centers for Disease Control and Prevention: audiometry (AUX),
demographics (DEMO) and audiometry questionnaire (AUQ) for four cycles.

| Cycle | Ages tested | Ears 6-19 | Ears 20-69 | Ears 70+ |
|---|---|---|---|---|
| 2009-10 (`_F`) | 12-19, 70+ | 2,483 | | 1,882 |
| 2011-12 (`_G`) | 20-69 | | 7,687 | |
| 2015-16 (`_I`) | 20-69 | | 8,589 | |
| 2017-March 2020 (`P_`) | 6-19, 70+ | 5,848 | | 2,572 |
| total | | 8,331 | 16,276 | 4,454 |

An ear is used if the examination was complete or partial (AUAEXSTS 1 or
2), the survey weight is positive, and thresholds exist at all seven
frequencies (first 1 kHz reading). "No response" (code 666) counts as
100 dB HL; code 888 (not measured) excludes the ear. NHANES does not
measure 250 Hz.

### 4.2 Weights, and the training and test groups

**Survey weights.** NHANES deliberately samples some groups more heavily
than others, and not everyone selected attends the examination. NCHS
therefore gives each examined participant a weight (`WTMEC2YR`;
`WTMECPRP` for 2017-March 2020): the number of US residents that
participant represents, built from the probability of selection, an
adjustment for non-attendance, and a final adjustment to Census population
totals by age, sex and ethnicity. One cycle's weights add up to the US
population. Where two cycles tested the same ages (12-19 in 2009-10 and
2017-20; 20-69 in 2011-12 and 2015-16; 70 and over in 2009-10 and
2017-20), each participant's weight is multiplied by their cycle's share of
the years those cycles span, as NCHS advises when combining cycles: 2/4
for each of 2011-12 and 2015-16, and 2/5.2 for 2009-10 against 3.2/5.2 for
the 3.2-year 2017-March 2020 file. Ages 6-11 come from one cycle only. All ears together then represent the US population
aged 6 and over once. Both ears of a participant carry the participant's
weight. No other population adjustment is made, so the population is
weighted once, by NCHS.

**Training weight.** An ear's training weight is its survey weight
multiplied by p(age), the proportion of ears with hearing loss at that
age, so the training population has the age profile of ears with hearing
loss. p(age) is a survey-weighted logistic regression of hearing loss (WHO:
a mean of 0.5, 1, 2 and 4 kHz of 20 dB HL or worse, in that ear) on age,
fitted on the training group:

logit p(age) = -1.8578 + 2.1794 z + 0.4609 z², where z = (age - 45) / 25.

| Age | 6 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80+ |
|---|---|---|---|---|---|---|---|---|---|
| p(age) | 1.6% | 1.8% | 2.7% | 4.7% | 9.3% | 19.7% | 40.5% | 68.6% | 89.1% |

The resulting share of the training weight by age is 1.7% (6-19), 6.4%
(20-39), 27.2% (40-59), 26.5% (60-69), 24.8% (70-79) and 13.4% (80 and
over), against population shares of 18.8%, 29.3%, 29.6%, 11.6%, 7.3% and
3.4%.

Hearing loss is defined by the WHO measure rather than by H, so that the
weighting does not depend on the number it trains. A smooth curve is used
rather than the prevalence in each age band because it has no arbitrary
band edges and it bridges the join between ages 69 and 70, which come from
different cycles; a cubic term did not improve the fit. NHANES records
ages over 80 as 80, so p(80) stands for everyone 80 and over (the observed
proportion there is 94%).

**Training and test groups.** Half of the participants in each age band
(6-19, 20-69, 70 and over; both ears together, chosen at random with a
fixed seed of 1) were set aside as a test group and not used to build the
table; the table is built from the other half, the training group. Every figure in section 5 is measured on the test
ears, so it describes the published table on ears it has never seen, as
it would meet a new person.

### 4.3 Training

The 50 shapes are a weighted k-means clustering of the training ears'
residual curves (seven values each), with k-means++ initialisation and 30
restarts (seeds 7-36). The restart kept is the one with the lowest weighted
inertia among those in which every shape rests on at least 10 effective
training ears (Kish's effective sample size, (sum of w)² / sum of w²), so
that no shape can be set by a few heavily weighted ears; the lowest-inertia
restart met this condition. The shapes are then ordered as in section 2.3
and rounded to 0.1 dB. Every shape represents many people: each has
between 72 and 4,528 NHANES ears assigned to it (median 302). The largest
is a near-flat normal shape.

The quick-test estimator (section 6.3) is a weighted least-squares
quadratic regression (all squares and pairwise products) from three
quick-test values to the seven thresholds, fitted on the same training
ears and weights.

### 4.4 Rebuilding the table

```text
pip install -r build/requirements.txt
python3 build/fetch_nhanes.py          # downloads 12 public files from CDC, checks SHA-256
python3 build/build_table.py --check   # rebuilds and compares with earnumber-v1.json
python3 build/make_figures.py          # figures/*.svg
python3 build/make_vectors.py          # earnumber-v1-vectors.json
```

`build_table.py` also writes the evaluation of section 5 to
`build/results.md`. The raw NHANES files are not redistributed; the fetch
script downloads them from CDC.

### 4.5 Data use

The NCHS data user agreement allows public-use files to be used for
statistical analysis and reporting, and forbids attempts to identify
anyone or to link the data with identifiable records. The published table
contains only aggregates: 50 average curves, regression coefficients, the
three coefficients of the prevalence curve and the six ANSI weights. No individual record is included.

## 5. Evaluation

All figures are on the test ears (section 4.2), with the survey weights,
so each age band is described as it occurs in the US population.

### 5.1 Accuracy of the decoded audiogram

Root mean square difference between the decoded and measured audiogram
over the seven frequencies, per ear:

| | 6-19 | 20-69 | 70+ |
|---|---|---|---|
| median | 4.5 dB | 4.5 dB | 5.1 dB |
| 90th percentile | 6.7 dB | 6.8 dB | 7.8 dB |
| ears worse than 10 dB | 0.6% | 1.7% | 2.6% |

Counted as the training weight counts them (weighted to hearing loss), the
median is 4.9 dB and the 90th percentile 7.5 dB. By WHO grade of the ear,
the median is 4.4 dB under 20 dB HL, 5.3 dB at 20-34, 5.4 dB at 35-49,
5.3 dB at 50-64 and 4.5 dB at 65 and over. By frequency (all ages,
population-weighted): 4.8 dB at 0.5 kHz, 4.6 at 1 kHz, 4.7 at 2 kHz, 5.6
at 3 kHz, 5.1 at 4 kHz and 5.6 at 6 and 8 kHz.

For scale, audiometers step in 5 dB and a repeated clinical audiogram
typically differs from the first by about 5 dB.

### 5.2 Stability

With the simulated retest of section 3.3, the quality level moves by two or
more steps in 0.8% (6-19), 1.2% (20-69) and 2.5% (70+) of ears.

| Group | Level unchanged | Moves one step | Moves two or more | Same shape | Identical number |
|---|---|---|---|---|---|
| 6-19 | 68.4% | 30.9% | 0.8% | 55.9% | 38.3% |
| 20-69 | 60.3% | 38.4% | 1.2% | 50.9% | 31.5% |
| 70+ | 54.3% | 43.2% | 2.5% | 55.2% | 31.0% |
| population | 61.2% | 37.6% | 1.3% | 52.2% | 32.7% |
| loss-weighted | 56.7% | 41.6% | 1.8% | 52.7% | 30.9% |

The last two digits are therefore not stable: about two ears in three get a
different number on retest. The real 1 kHz repeat (section 3.3) differs by
a standard deviation of 3.2 dB (n = 29,023 ears), so the simulated retest
is cautious for a repeat in the same session.

### 5.3 Ranking against self-reported hearing

Spearman correlation between the better ear's number and the six-point
self-report (excellent to deaf): 0.62 at 70+, 0.37 at 20-69 and 0.08 at
6-19. The low figures in younger people reflect how few of them report any
difficulty, which leaves little to rank, rather than a weakness of the
number.

### 5.4 Distribution

Percentiles 5 / 25 / 50 / 75 / 95 of the number:

| 6-19 | 20-69 | 70+ |
|---|---|---|
| 879 / 944 / 981 / 994 / 998 | 637 / 826 / 896 / 946 / 994 | 356 / 524 / 657 / 770 / 876 |

### 5.5 Codes that do not occur

Every number decodes, but 207 of the 1,000 do not re-encode to themselves.
All are combinations of a very poor level with a steep shape (or the best
level with a shape below -10 dB) whose decoded audiogram runs past the
audiometric limits and is clipped; such ears do not exist. All other 793
numbers, including the reserved 000, re-encode exactly. The level differs
for 104 of the 207.

### 5.6 Other schemes on the same ears

**Hearing Number.** The Hearing Number promoted by Johns Hopkins University
(hearingnumber.org) is the four-frequency pure-tone average in dB, lower
being better. It is the measure adopted by the US consumer standard
ANSI/CTA-2118 (2023), and WHO grades are bands of it. It is a single
average. The "level only" row of section 3.4 shows what a single average
can decode to: 9.2 / 17.0 dB median and 90th percentile error with the
typical shape of its level (that row uses H, which weights the frequencies
differently from the four-frequency average).

**LCH triad.** Humes and Zapala (2024) give three digits per ear, each the
mean threshold of a band (0.5-2 kHz, 3-6 kHz, 8 kHz) in 10 dB steps, 0
best and 9 worst. Its authors evaluated it on NHANES adults and two
clinical datasets. On the test ears here, loss-weighted:

| | Ear Number | LCH triad, band midpoints | LCH triad, training mean audiogram |
|---|---|---|---|
| median / 90th percentile error (dB) | 4.9 / 7.5 | 7.1 / 11.8 | 5.5 / 9.1 |
| ears over 10 dB | 2.2% | 18.9% | 5.6% |

| | Ear Number | LCH triad |
|---|---|---|
| pairs ordered as H when read as one number (triad: lower is better) | 95.7% | 93.6% |
| identical code on the simulated retest | 31% | 42% |
| distinct codes used by all ears | 712 | 402 |

The triad needs no table, each digit can be read directly, and it is
steadier on retest. Ear Number decodes more closely, especially for the
worst-described ears (2.2% over 10 dB against 5.6% at best for the triad),
and is one ordered scale.

**Earlier work.** The design resembles standard audiograms by vector
quantisation (Bisgaard et al. 2010), rule-based audiogram classification
(Margolis and Saly 2007; Charih et al. 2020) and cluster analysis of
NHANES audiograms (Ciletti and Flamme 2008).

## 6. Using Ear Number

### 6.1 In Python

`earnumber.py` uses only the Python standard library.

```python
import earnumber as en
ear = {500: 10, 1000: 15, 2000: 25, 4000: 45, 8000: 60}
n = en.encode(ear)              # an int 0-999
en.decode(n)                   # {250: ..., 500: ..., ..., 8000: ...} in dB HL
en.quality_level(n), en.shape_index(n)
en.format_pair(n, 688)         # 'LLL 688 C': left, right, check digit
en.format_pair(456, 456, True, '', 'N')   # '456 456N 1': right ear not measured
en.parse_pair('705,688,4')     # reads any written form and verifies the check digit
```

From the command line:

```text
python3 earnumber.py encode 500=10 1000=15 2000=25 4000=45 8000=60
python3 earnumber.py decode 705
python3 earnumber.py check 705 688      # prints 705 688 4
```

### 6.2 From a clinical audiogram

Use the air-conduction thresholds of each ear. The number is exact for the
audiogram given; its precision is that of the audiogram.

### 6.3 From a short self-test

A short test that measures the 1 kHz threshold, the edge frequency (where
the threshold first rises 20 dB above the 1 kHz one) and one more point can
estimate the audiogram with `estimate_from_quick`, which is then encoded.
Two variants are provided: the third point at an inner frequency between
1 kHz and the edge, or at 8 kHz. On the test ears (population-weighted)
the coded estimate decodes with the following median / 90th percentile
error, and the quality level lands within one step of the true level for
the share shown:

| Input | Inner point | 8 kHz |
|---|---|---|
| error-free | 7.0 / 13.6 dB; 97% | 6.4 / 10.6 dB; 97% |
| test noise | 7.6 / 14.4 dB; 93% | 7.0 / 11.6 dB; 91% |
| test noise plus calibration offset | 9.0 / 17.2 dB; 74% | 8.1 / 14.4 dB; 74% |

The error model adds independent noise of 4 dB (standard deviation) to the
1 kHz value and to the third value, 0.15 octave to the edge frequency, and
a calibration offset of 7 dB common to both thresholds of the ear. Under
the realistic condition (test noise plus calibration offset) an E number
lands within one level of the true level for 74% of ears, about three in
four. The 7 dB calibration figure comes from one phone and may be larger on
other devices.

The inputs must be in dB HL. Phones and earphones are not calibrated
audiometers, and their error can exceed 10 dB, so numbers from self-tests
carry the suffix E (section 2.7) unless the device has been calibrated.

### 6.4 Versions and extensions

A number is meaningful only with the table that made it. Version 1 numbers
must always be decoded with version 1 of the table; a later table will
carry a new version, and a finer version may use four digits per ear, so
that the length of a number identifies its scheme (six or seven digits
for version 1, eight or nine for a four-digit version). Ears with unusual
audiograms (for example a low-frequency loss, or a conductive component
that bone-conduction devices could use) still receive a correct quality
level and the nearest shape; the reserved suffix letters (section 2.7)
leave room to mark such features in later versions.

**Version identity.** The version 1 table is the file `earnumber-v1.json`
whose SHA-256 is
`479155629f5a377a2de0dbc82d1ad83908692ce78cf505ef75e1ec9687f6c97d`;
`earnumber.py` verifies it on loading.

**Conformance.** `earnumber-v1-vectors.json` holds all 1,000 decodes, 276
audiograms with their expected numbers (including every level boundary and
near-ties), and check digits and written forms that must be accepted or
rejected. A port in another language must reproduce it, with decoded
values within 0.05 dB.

## 7. Limitations

- Ear Number describes air-conduction thresholds only. It does not capture
  hearing in noise, loudness tolerance, tinnitus, or whether a loss is
  conductive or sensorineural.
- NHANES does not measure 250 Hz or above 8 kHz; the table knows nothing
  of either.
- The training data is a survey of the US population. Shapes common
  elsewhere but rare there may be represented less well.
- The shapes are weighted towards hearing loss, so normal hearing and
  children's ears decode 0.3-0.6 dB less accurately than population
  weighting would give. The 70-and-over group still decodes slightly less
  accurately than younger groups, because their audiograms vary more.
- Ears without thresholds at all seven frequencies are left out without
  adjustment (3-18% of examined people by age, 30% at 6-11), on the
  assumption that within an age a missing value does not depend on hearing.
- Self-reported hearing, used to choose how frequencies are combined, is a
  noisy criterion; it can reject clearly worse formulas but cannot separate
  close ones.
- Numbers estimated from uncalibrated devices inherit the device's error.
- The last two digits are not stable on retest (section 5.2).
- The evidence is thin at the bottom of the scale. Levels 0 to 5 hold 36,
  32, 30, 35, 76 and 82 ears of the 29,061 (level 19 holds 7,178). Ears
  with H of 65 dB or more number 422, and with H of 80 dB or more 133.
- The table has a single shape for losses that are worse in the bass than
  in the treble.
- The number gives thresholds in absolute decibels, so a device needs to
  know its own output level to use the level part exactly. Without that it
  can use the pattern and degree only as a starting point.
- Ear Number does not say how a device should compensate.

## 8. References

- American National Standards Institute (1997, reaffirmed 2017). ANSI
  S3.5-1997, Methods for calculation of the speech intelligibility index.
- Bailey IL, Lovie JE (1976). New design principles for visual acuity
  letter charts. American Journal of Optometry and Physiological Optics
  53: 740-745.
- Kish L (1965). Survey Sampling. New York: Wiley. (Effective sample size.)
- Damm HM (2004). Total anti-symmetrische Quasigruppen. Dissertation,
  Philipps-Universitaet Marburg.
- Bisgaard N, Vlaming MSMG, Dahlquist M (2010). Standard audiograms for the
  IEC 60118-15 measurement procedure. Trends in Amplification 14(2):
  113-120. (A related distillation of audiograms into ten standard shapes.)
- ANSI/CTA-2118 (2023). Four frequency pure tone average testing
  methodology and reporting metrics for consumer facing hearing solutions.
  Consumer Technology Association.
- Charih F, Bromwich M, Mark AE, Lefrancois R, Green JR (2020). Data-driven
  audiogram classification for mobile audiometry. Scientific Reports
  10(1): 3962. doi:10.1038/s41598-020-60898-3
- Ciletti L, Flamme GA (2008). Prevalence of hearing impairment by gender
  and audiometric configuration: results from the National Health and
  Nutrition Examination Survey (1999-2004) and the Keokuk County Rural
  Health Study (1994-1998). Journal of the American Academy of Audiology
  19: 672-685.
- Humes LE, Zapala DA (2024). Easy as 1-2-3: development and evaluation of
  a simple yet valid audiogram-classification system. Trends in Hearing
  28: 23312165241260041. doi:10.1177/23312165241260041
- Johns Hopkins Cochlear Center for Hearing and Public Health. Hearing
  Number. https://hearingnumber.org
- Margolis RH, Saly GL (2007). Toward a standard description of hearing
  loss. International Journal of Audiology 46: 746-758.
  doi:10.1080/14992020701572652
- Mueller HG, Killion MC (1990). An easy method for calculating the
  articulation index. The Hearing Journal 43(9): 14-17.
- National Center for Health Statistics. National Health and Nutrition
  Examination Survey, audiometry, demographics and audiometry
  questionnaire data, cycles 2009-2010, 2011-2012, 2015-2016 and
  2017-March 2020 (pre-pandemic). https://wwwn.cdc.gov/nchs/nhanes/
- National Center for Health Statistics. NHANES tutorials: weighting
  (combining survey cycles). https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx
- National Center for Health Statistics. Data user agreement.
  https://www.cdc.gov/nchs/data_access/restrictions.htm
- World Health Organization (2021). World report on hearing. Geneva: WHO.

## Citation

Hill N (2026). Ear Number: a three-digit description of an ear's hearing.
Version 1.
