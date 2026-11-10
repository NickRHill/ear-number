# Ear Number v1: build evaluation

Table trained with the **loss** weighting. Aggregates only; all error figures are on the test group (the half of persons not used for training) unless stated.

## Data (ears with a complete 7-frequency audiogram, valid exam)

| Cycle | 6-19 | 20-69 | 70+ |
|---|---|---|---|
| 2009-10 | 2483 | 0 | 1882 |
| 2011-12 | 0 | 7687 | 0 |
| 2015-16 | 0 | 8589 | 0 |
| 2017-Mar 2020 | 5848 | 0 | 2572 |
| all ears | 8331 | 16276 | 4454 |
| persons | 4199 | 8162 | 2247 |
| test-group ears | 4167 | 8144 | 2230 |

Weights: each person's NHANES MEC weight x their cycle's years / total years of the cycles covering their age; overall rows use these (US population aged 6+). Loss weighting multiplies them by p(age), the prevalence of hearing loss per ear (WHO: mean of 0.5, 1, 2, 4 kHz >= 20 dB HL), fitted on the training half: logit p = -1.8578 + 2.1794 z + 0.4609 z^2, z = (age - 45) / 25.

| Age | 6 | 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 |
|---|---|---|---|---|---|---|---|---|---|
| p(age) | 1.6% | 1.8% | 2.7% | 4.7% | 9.3% | 19.7% | 40.5% | 68.6% | 89.1% |

## Decode RMS per ear over 0.5-8 kHz (dB; survey-weighted median / 90th percentile; share above 10 dB)

| 6-19 | 20-69 | 70+ | overall (population-weighted) |
|---|---|---|---|
| 4.5 / 6.7; 0.6% | 4.5 / 6.8; 1.7% | 5.1 / 7.8; 2.6% | 4.6 / 6.9; 1.6% |

Loss-weighted (ears counted in proportion to hearing loss at their age): median 4.9, 90th percentile 7.5.

By WHO grade of the ear (mean of 0.5, 1, 2, 4 kHz; median RMS, test-group ears in brackets):

| under 20 | 20-34 | 35-49 | 50-64 | 65 and over |
|---|---|---|---|---|
| 4.4 (10829) | 5.3 (2220) | 5.4 (932) | 5.3 (388) | 4.5 (172) |

## Decode RMS per frequency (dB, across test-group ears)

| Band | 0.5 kHz | 1 kHz | 2 kHz | 3 kHz | 4 kHz | 6 kHz | 8 kHz |
|---|---|---|---|---|---|---|---|
| 6-19 | 4.6 | 4.4 | 4.3 | 5.1 | 5.0 | 5.4 | 5.8 |
| 20-69 | 4.7 | 4.5 | 4.7 | 5.7 | 5.1 | 5.5 | 5.5 |
| 70+ | 5.5 | 5.3 | 5.6 | 6.1 | 5.4 | 6.1 | 6.0 |
| all | 4.8 | 4.6 | 4.7 | 5.6 | 5.1 | 5.6 | 5.6 |

## Spearman rho of the better ear's code with the six-point self-report (test-group persons with both ears; n in brackets)

| 6-19 | 20-69 | 70+ | all |
|---|---|---|---|
| 0.075 (2068) | 0.368 (4061) | 0.623 (1107) | 0.460 (7236) |

## Retest stability: share of test-group ears whose level moves 2+ steps (4 dB per frequency + 2 dB common noise, 5 dB rounding)

| 6-19 | 20-69 | 70+ | overall |
|---|---|---|---|
| 0.8% | 1.2% | 2.5% | 1.3% |

## Code by age band (test-group ears, survey-weighted percentiles 5 / 25 / 50 / 75 / 95)

| 6-19 | 20-69 | 70+ |
|---|---|---|
| 850-899 / 900-949 / 950-999 / 950-999 / 950-999 | 600-649 / 800-849 / 850-899 / 900-949 / 950-999 | 350-399 / 500-549 / 650-699 / 750-799 / 850-899 |

Within a block of 50 the last digits identify the shape and do not rank hearing.

## Quick-test path (estimated audiogram, then coded; RMS median / 90th pct; level within 1 step of the true level)

| Variant | 6-19 | 20-69 | 70+ | overall |
|---|---|---|---|---|
| 1 kHz, edge, inner point | 6.3 / 10.8; 98% | 7.0 / 13.7; 97% | 8.5 / 16.3; 95% | 7.0 / 13.6; 97% |
| 1 kHz, edge, 8 kHz | 6.1 / 9.1; 99% | 6.4 / 10.7; 97% | 7.6 / 12.6; 95% | 6.4 / 10.6; 97% |

## Round trip, encode(decode(n)) == n, over all 1000 codes

207 codes do not round-trip (codes whose decoded audiogram is clipped at -10 or 100 dB); the level differs for 104. The reserved number 000 (100 dB at every frequency, no hearing) does round-trip.

## Shape occupancy

Ears assigned to each shape (all 29061 ears): minimum 72 (shape 13), median 302, maximum 4528. Training half only: minimum 28.

## What the numbers signify

Better ear's code (higher = better hearing) for persons with both ears measured, by how they rate their own hearing (all persons, both halves; survey-weighted median and quartiles Q1 / median / Q3; n = persons; cells with n < 10 suppressed). Each code is shown as its block of 50; within a block the last digits identify the shape and do not rank hearing. The all-ages group is survey-weighted to the US population.

### Self-report (without aid)

| Category | 70+: Q1 / median / Q3 (n) | 20-69: Q1 / median / Q3 (n) | all ages: Q1 / median / Q3 (n) |
|---|---|---|---|
| excellent | 700-749 / 750-799 / 800-849 (386) | 850-899 / 900-949 / 950-999 (3138) | 850-899 / 900-949 / 950-999 (6029) |
| good | 650-699 / 750-799 / 800-849 (688) | 850-899 / 900-949 / 950-999 (3533) | 850-899 / 900-949 / 950-999 (5644) |
| a little trouble | 550-599 / 600-649 / 700-749 (579) | 750-799 / 800-849 / 900-949 (993) | 700-749 / 800-849 / 900-949 (1747) |
| moderate trouble | 500-549 / 550-599 / 650-699 (326) | 650-699 / 750-799 / 850-899 (325) | 550-599 / 700-749 / 800-849 (670) |
| a lot of trouble | 350-399 / 450-499 / 500-549 (214) | 450-499 / 600-649 / 750-799 (118) | 400-449 / 500-549 / 600-649 (341) |
| deaf | 200-249 / 250-299 / 350-399 (14) | n<10 | 000-049 / 250-299 / 350-399 (19) |

### Functional ladder, 2017-20 (ages 6-19 and 70+ only)

| Category | 70+: Q1 / median / Q3 (n) | 6-19: Q1 / median / Q3 (n) | 6-19 and 70+: Q1 / median / Q3 (n) |
|---|---|---|---|
| excellent or good | 700-749 / 750-799 / 800-849 (626) | 900-949 / 950-999 / 950-999 (2754) | 850-899 / 950-999 / 950-999 (3380) |
| hears a whisper | 550-599 / 650-699 / 700-749 (192) | 850-899 / 900-949 / 950-999 (70) | 600-649 / 650-699 / 800-849 (262) |
| hears a normal voice | 500-549 / 600-649 / 650-699 (233) | 850-899 / 900-949 / 950-999 (57) | 550-599 / 600-649 / 700-749 (290) |
| hears a shout | 450-499 / 500-549 / 600-649 (172) | 700-749 / 800-849 / 900-949 (11) | 450-499 / 500-549 / 600-649 (183) |
| hears loud speech into the ear | 300-349 / 400-449 / 500-549 (24) | n<10 | 300-349 / 400-449 / 500-549 (24) |
| none of these | 200-249 / 250-299 / 400-449 (11) | n<10 | 200-249 / 250-299 / 400-449 (11) |


## Where the error comes from (test group; median / 90th percentile in dB; loss-weighted, and 70+ population-weighted)

| Variant | loss-weighted | 70+ |
|---|---|---|
| shipped (5 dB level, 50 shapes) | 4.9 / 7.5 | 5.1 / 7.8 |
| exact level, nearest shape | 4.6 / 7.2 | 4.9 / 7.6 |
| 5 dB level, exact shape (|level centre - H|) | 1.3 / 2.3 | 1.3 / 2.3 |
| level only, plus the typical shape of that level | 9.2 / 17.0 | 9.9 / 17.4 |
| worst single frequency, shipped | 8.6 / 13.6 | 9.1 / 14.0 |
| worst single frequency, level only | 16.6 / 31.3 | 17.5 / 30.9 |

The typical shape of a level is the training-half loss-weighted mean residual of the ears at that level.

## Retest detail (simulated retest as in the stability section; test group)

| Group | level unchanged | moves one step | moves two or more | same shape | identical number |
|---|---|---|---|---|---|
| 6-19 | 68.4% | 30.9% | 0.8% | 55.9% | 38.3% |
| 20-69 | 60.3% | 38.4% | 1.2% | 50.9% | 31.5% |
| 70+ | 54.3% | 43.2% | 2.5% | 55.2% | 31.0% |
| population | 61.2% | 37.6% | 1.3% | 52.2% | 32.7% |
| loss-weighted | 56.7% | 41.6% | 1.8% | 52.7% | 30.9% |

## Real repeat of the 1 kHz reading (NHANES measures it twice)

Over all 29023 ears where both readings are valid thresholds (neither a no-response 666, nor missing, nor at 100 dB or above): standard deviation of the difference 3.24 dB; share differing by 10 dB or more 2.7%.

## Order of the numbers (400000 random pairs of test ears, drawn with loss weights; pairs with different numbers only)

| Gap between the two numbers | pairs | higher number has the lower H (ties count half) | same level |
|---|---|---|---|
| all pairs with different numbers | 398565 | 95.7% | 9.4% |
| 1-9 | 17268 | 52.3% | 98.8% |
| 10-24 | 18272 | 61.7% | 85.8% |
| 25-49 | 30854 | 93.4% | 15.1% |
| 50 or more | 332171 | 100.0% | 0.0% |

## Design comparisons (trained on the training half with loss weights; test group, loss-weighted)

| Design | codes | median / 90th percentile RMS (dB) | share of ears over 10 dB |
|---|---|---|---|
| shipped, 50 shapes | 1000 | 4.9 / 7.5 | 2.2% |
| 10 shapes (k-means) | 200 | 6.0 / 9.5 | 8.1% |
| 20 shapes (k-means) | 400 | 5.4 / 8.5 | 4.8% |
| 100 shapes (k-means) | 2000 | 4.4 / 6.8 | 1.3% |
| two-parameter formula: 10 x 5 lattice on two principal components | 1000 | 5.3 / 8.6 | 4.8% |
| LCH triad, decoded to band midpoints | 1000 | 7.1 / 11.8 | 18.9% |
| LCH triad, decoded to each triad's training mean audiogram | 1000 | 5.5 / 9.1 | 5.6% |

k-means designs: 5 dB level, 3 restarts (seeds 7-9), lowest inertia kept. The LCH triad (Humes and Zapala 2024) is floor(mean threshold / 10), clipped 0-9, for L = 0.5, 1, 2 kHz, C = 3, 4, 6 kHz and H = 8 kHz.

| Code | pairs ordered as H when read as one number (triad: lower is better) | identical code on the simulated retest | distinct codes used by all ears |
|---|---|---|---|
| Ear Number | 95.7% | 31% | 712 |
| LCH triad | 93.6% | 42% | 402 |

## Self-test with input error (all test ears, population-weighted; RMS median / 90th percentile; level within 1 step)

| Input | 1 kHz, edge, inner point | 1 kHz, edge, 8 kHz |
|---|---|---|
| error-free | 7.0 / 13.6; 97% | 6.4 / 10.6; 97% |
| test noise | 7.6 / 14.4; 93% | 7.0 / 11.6; 91% |
| test noise plus calibration offset | 9.0 / 17.2; 74% | 8.1 / 14.4; 74% |

Noise model: independent N(0, 4 dB) on the 1 kHz value and on the third value; N(0, 0.15) octave on log2(edge), edge kept within 1000-16000 Hz; calibration offset N(0, 7 dB) common to both thresholds of the ear. Fixed seed.

## Ears per level and severe losses (all ears)

| Level | 19 | 18 | 17 | 16 | 15 | 14 | 13 | 12 | 11 | 10 | 9 | 8 | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ears | 7178 | 7195 | 4428 | 2862 | 1848 | 1344 | 1030 | 789 | 635 | 527 | 382 | 250 | 171 | 131 | 82 | 76 | 35 | 30 | 32 | 36 |

Ears with H of 50 dB or more: 1225; 65 dB or more: 422; 80 dB or more: 133.

