# Customer Churn Prediction

Live app: https://customer-churn-prediction-rahul.streamlit.app/

## What this project is

This is an end to end applied machine learning project where I took a customer churn prediction model all the way from raw data to a live, working application that anyone can open and try. I built this specifically to go beyond just training a model in a notebook, since a model that only exists in a Jupyter notebook can't actually be used by anyone else. I wanted something I could point to and say here, try it yourself, and have it just work.

## The business question

Given how often a customer has purchased and how much they've spent, can I predict whether they're likely to stop buying from this business, and can I turn that prediction into something a real business could actually use to prioritize who to reach out to.

## Where the data comes from

I reused the cleaned Online Retail II dataset from an earlier project of mine, a customer segmentation and retention analysis I built using RFM analysis and K-means clustering. That project is here if you want to see how the data was originally cleaned: https://github.com/Rahulkulkarni2002/customer-segmentation-retention-analysis

Since I already had a clean, well understood dataset with Recency, Frequency, and Monetary features already built for each customer, it made sense to reuse it here rather than start over with a brand new dataset. The full dataset covers about 804,000 transactions across roughly 5,855 customers, over two years from December 2009 to December 2011.

## How I defined churn

I didn't have a churn label handed to me, so I had to define one myself. I used Recency, which is how many days it's been since a customer's last purchase, and defined churn as any customer who hasn't purchased in the last 90 days. I picked 90 days deliberately rather than an arbitrary number. The median Recency across all customers was already around 95 days, so a 90 day cutoff gave me a genuinely balanced target, about 50.7 percent churned and 49.3 percent active, rather than something heavily skewed where almost everyone or almost no one is labeled churned. A shorter cutoff like 30 days would have classified most of the customer base as churned, which wouldn't have been a useful label for a business to act on.

## Features and a leakage mistake I avoided

For features I engineered several things from the raw transaction data. Frequency and Monetary came directly from the existing RFM table. I also added Tenure, which is the number of days between a customer's first and last purchase, calculated straight from the transaction dates. I added AvgOrderValue, which is Monetary divided by Frequency, since spend per order is a genuinely different signal than either raw number alone. I log transformed Frequency and Monetary since both were right skewed, and I added an interaction term multiplying Frequency and Monetary together, so the models could see combined high frequency, high spend behavior directly.

One thing I want to call out specifically is that I deliberately did not include Recency as a feature in the model. Recency is literally what I used to create the Churned label in the first place, so if I'd included it as a feature, the model would essentially just be learning the rule I used to build the label, which isn't real prediction, it's circular. I checked for this kind of leakage before training anything, not after.

## Model comparison

I didn't just pick one model and go with it. I trained and compared six different approaches on the same train test split, using the same features, so the comparison would actually be fair.

First I tried a simple two feature version using just Frequency and Monetary, comparing Logistic Regression against XGBoost. XGBoost barely beat the simple linear model, which told me there wasn't much complex nonlinear signal for a more sophisticated model to exploit with just two features.

Then I expanded to the full seven feature set described above and tried Logistic Regression, XGBoost, a neural network using scikit learn's MLPClassifier, and Random Forest. This time the richer features actually helped every model improve, and the differences between models became more meaningful.

I also tried combining models into a voting ensemble, first with three models and then with four, including Random Forest. The four model ensemble ended up performing almost identically to the three model version, which told me Random Forest wasn't adding much new information on top of what the other models were already capturing.

**Here's the honest comparison across everything I tried, measured on the same held out test set (1,171 customers).**

| Model | Features | Accuracy | Recall | F1 score |
|---|---|---|---|---|
| Logistic Regression | 2 | 69.0% | 82.5% | 0.730 |
| XGBoost | 2 | 69.4% | 76.4% | 0.717 |
| Logistic Regression | 7 | 71.0% | 74.9% | 0.724 |
| XGBoost | 7 | 71.9% | 79.8% | 0.742 |
| Neural Network (MLP) | 7 | 72.2% | 80.6% | 0.746 |
| **Random Forest (chosen)** | **7** | **72.4%** | **81.0%** | **0.749** |
| Ensemble of 3 models | 7 | 72.8% | 79.0% | 0.746 |
| Ensemble of 4 models | 7 | 72.8% | 79.5% | 0.747 |

**Random Forest had the best F1 score of any single model and caught 81.0 percent of churners (recall).** Only the 2 feature Logistic Regression recalled slightly more (82.5 percent), but with much lower accuracy. The two ensembles were about 0.4 points more accurate but no better on F1, so they added complexity without a real gain.

In the end I chose Random Forest as the model I actually deploy, not because it's the most complex option, but because it matched or beat every more complicated alternative, including the ensembles, while being much simpler to actually put into production. That felt like the right tradeoff for a real deployed system rather than chasing a marginal, possibly noisy improvement from added complexity.

## Experiment tracking

I used MLflow to track all six models I trained, logging the parameters, accuracy, precision, recall, and F1 score for each one, along with saving the actual trained model files. I ran into a couple of real environment issues along the way, MLflow initially refused to save the XGBoost and neural network models because of a security check on untrusted object types, which I resolved by using XGBoost's own dedicated logging function and explicitly marking the specific neural network internal type as trusted. I also had the MLflow web dashboard fail to show my logged runs for a while, which turned out to be a mismatch between where the tracking data was actually saved and where the dashboard was looking, not a problem with my actual training code. I confirmed this directly using MLflow's Python client rather than just trusting the browser, and found all my runs were genuinely saved correctly the whole time.

## Building the API

I built a FastAPI application that loads and trains the Random Forest model once when the server starts, then exposes a predict endpoint that takes in a customer's Frequency, Monetary, and Tenure, calculates the same engineered features used in training, and returns both a churn prediction and the underlying probability. I added input validation so that invalid input, like a Frequency of zero which would cause a divide by zero error when calculating average order value, returns a clean error message instead of crashing the server. I tested this using FastAPI's automatic interactive documentation page and confirmed both the validation and the actual predictions work correctly.

## The deployed app

For the live, publicly deployed version, I built a self contained Streamlit application rather than running the API and the interface as two separate connected services. The model is trained once and cached using Streamlit's caching decorator, so it doesn't retrain on every single interaction. Someone visiting the live app can type in a customer's order count, total spend, and how long they've been a customer, click a button, and immediately see a churn prediction along with the probability behind it.

I made this choice deliberately after thinking about whether I actually needed two separate running services for this to be a real, legitimate applied ML project. The FastAPI version still exists in this repository and demonstrates that I can build a real API that other software could call, but for the version anyone can actually visit and use right now, a single self contained app was simpler to deploy and just as complete from a user's perspective.

## Going further, predicting who will leave next

Everything above uses one snapshot, where the churn label and the features come from the same two year window. That finds customers who have already gone quiet. A business needs to know who is about to leave, so I rebuilt the problem to look forward. I picked a cutoff date, 10 September 2011, which is 90 days before the data ends. Every feature is built only from what happened before that date, and churn means the customer made no purchase in the 90 days after it. That gave me 5,258 customers, and 56.4 percent of them did not buy again in the next 90 days. Because Recency is now measured at the cutoff, before the label period starts, it is a fair feature here and I added it to the same seven features.

**I compared the same four algorithms on this forward looking version, 4,206 customers to train and 1,052 held out to test.**

| Model | Accuracy | Recall | F1 score | AUC |
|---|---|---|---|---|
| Logistic Regression | 74.0% | 80.1% | 0.777 | 0.809 |
| XGBoost | 75.6% | 84.0% | 0.795 | 0.819 |
| Neural Network (MLP) | 75.0% | 83.7% | 0.791 | 0.816 |
| **Random Forest** | **76.2%** | **85.5%** | **0.803** | 0.818 |

**Random Forest was again the best, on accuracy, recall and F1.** All four models are close, which told me the features matter more than the choice of algorithm. Without Recency the same Random Forest drops to 72.1 percent accuracy, so Recency is the strongest signal.

### Checking that the result is real

I checked for overfitting. Random Forest scored 76.6 percent accuracy on the training customers and 76.2 percent on the held out customers, so it is not memorising. Five fold cross validation gave an AUC of 0.797, between 0.793 and 0.802 on every fold, so about 0.80 is the honest AUC.

I also ran a stricter test, training the models at an earlier cutoff, 12 June 2011, and testing them on all 5,258 customers at the later cutoff. The AUC held at about 0.79 to 0.80 for every model, so the ranking of customers by churn risk is stable over time. Accuracy dropped to about 70 percent, level with a simple rule that flags anyone with no purchase in 90 days, and the reason is seasonality. In the summer training window 67.8 percent of customers went quiet, but before Christmas only 56.4 percent did, so a model trained on summer flags too many customers in autumn. The honest conclusion is that the model is useful for ranking customers by risk, and the cut off for calling someone churned needs to be reset for the season.

### What the result means in customers

Of the 1,052 held out customers, 594 really stopped buying. The model caught 508 of them, which is 85.5 percent, with 164 false alarms and 86 missed. The simple rule caught 494 with 191 false alarms, so the model finds 14 more leavers with 27 fewer false alarms. That is a real but modest gain.

The model is more useful for ranking. I ranked all 5,258 customers by predicted risk, using the model trained on the earlier period.

| Risk group | Customers | Stopped buying | Share of prior year spend |
|---|---|---|---|
| Riskiest 20% | 1,052 | 85.8% | 1.2% |
| High | 1,051 | 74.9% | 4.4% |
| Middle | 1,052 | 63.2% | 9.4% |
| Low | 1,051 | 41.8% | 14.7% |
| Safest 20% | 1,052 | 16.5% | 70.2% |

The ranking works, but the riskiest group spends very little, so it is not where the money is.

**The model is most valuable among high value customers.** The top 25 percent of customers by spend, 1,315 customers, bring in 82.6 percent of revenue, and 21.1 percent of them stopped buying. Within that group the model's riskiest 20 percent, 263 customers who spent about 854 thousand pounds in the prior year, stopped buying 46.4 percent of the time, against 4.6 percent for its safest 20 percent. Those are the customers worth contacting first.

The API and the live app above still use the snapshot Random Forest. Moving them to this forward looking model is the next step.

## What I'd do differently with more time

The first thing I would do is move the live app and the API from the snapshot model to the forward looking model, so the deployed version answers the real business question. I would also train on several cutoff dates across the year and add seasonal features, since the strictest test showed that churn rates change a lot between summer and the weeks before Christmas. After that I would test whether features like product categories or country give the more complex models a real advantage, and I would connect the deployed app to the MLflow tracked model files instead of retraining at startup, since that is closer to how a real production system works.

## How to run this yourself

To run the notebook, download this repository, open a terminal in its folder and install the packages with `pip install -r requirements-notebook.txt`. Then open `churn.ipynb` in Jupyter or VS Code and choose Run All. The data files are included, so nothing else needs downloading, and the whole notebook runs in under a minute.

To run the app on your own computer, install the packages with `pip install -r requirements.txt` and start it with `streamlit run streamlit_app.py`. To run the API, also install fastapi and uvicorn, then start it with `uvicorn main:app --reload` and open http://127.0.0.1:8000/docs to try it.

## Files in this repository

churn.ipynb contains the full analysis, from loading the data through training and comparing the models, then the forward looking version and the results in numbers of customers.

main.py is the FastAPI application, meant to be run locally with uvicorn.

app.py is the original two service version of the Streamlit app that calls the FastAPI endpoint over the network, kept here to show that architecture works.

streamlit_app.py is the self contained version actually deployed live, with the model built directly into the app.

requirements.txt lists the Python packages the live app needs, and requirements-notebook.txt lists the ones needed to run the notebook.

cleaned_retail.csv and rfm_table.csv are the underlying cleaned dataset and RFM feature table, reused from the companion segmentation project.

## Tools and skills used

Python, pandas, numpy, scikit learn, XGBoost, MLflow, FastAPI, Streamlit, and Streamlit Community Cloud for deployment.
