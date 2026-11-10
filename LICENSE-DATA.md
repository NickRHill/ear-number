# Licence for the documents and the table

The following are licensed under the Creative Commons Attribution 4.0 International licence
(CC BY 4.0, https://creativecommons.org/licenses/by/4.0/):

- `paper.md`
- `README.md`
- `earnumber-v1.json`
- everything in `figures/`

Attribution: "Nicholas Hill, Ear Number".

The code (`earnumber.py`, `build/`, `tests/`) is under the MIT licence; see `LICENSE`.

## Data source

`earnumber-v1.json` is derived from public-use data of the National Health and Nutrition
Examination Survey (NHANES), National Center for Health Statistics (NCHS), Centers for Disease
Control and Prevention: the audiometry, demographics and hearing questionnaire files for 2009-10,
2011-12, 2015-16 and 2017-March 2020. The NCHS data user agreement allows the use of these files
for statistical analysis and reporting. This package contains only aggregate results (fifty
average curves, regression coefficients and summary tables) and no individual records. The NHANES
files are downloaded from the CDC site by `build/fetch_nhanes.py` and are not redistributed here.

Please cite NCHS as the source of the underlying data: National Center for Health Statistics,
National Health and Nutrition Examination Survey, https://www.cdc.gov/nchs/nhanes/. NCHS has not
endorsed this work and is not responsible for its analysis or conclusions.
