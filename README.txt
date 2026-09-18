# Car Price Fairness Estimator (Divar listings)

Given a used car's specs and asking price, estimates the fair market
price, a plausible price range, and whether the asking price is
Below Market / Fair / Above Market -- with supporting comparable
vehicles and a confidence level.

For methodology, results, limitations, and next steps, see
**[REPORT_fa.md](REPORT_fa.md)** (in Persian, per the assignment).
For 5 real example outputs, see **[sample_outputs.md](sample_outputs.md)**.

## How to run

'''
pip install -r requirements.txt   # pandas, numpy, pyyaml, scikit-learn,
                                   # lightgbm, matplotlib, seaborn
'''

Open the notebooks in order (each reads the previous step's saved
output from 'data/processed/', so they can be re-run independently
once the earlier steps have been run once):

1. 'notebooks/01_cleaning_normalization_cell.ipynb' -- cleans the raw scrape
   and saves 'data/processed/divar_cars_clean.csv' + 'divar_cars_normalized.csv'
2. 'notebooks/02_eda.ipynb' -- exploratory analysis (run after step 1)
3. `notebooks/03_modeling.ipynb` -- feature engineering, baseline,
   LightGBM model, quantile intervals with conformal calibration,
   validation, and the final `estimate_price()` function

All paths and cleaning thresholds are in `config/config.yaml`. The
brand name dictionary used for brand extraction is in
`config/brands.yaml` -- to add a brand the pipeline doesn't recognize,
edit that file (no code changes needed); run
`report_unknown_brands()` (in `src/normalize.py`) after ingesting new
data to see which values need adding.

