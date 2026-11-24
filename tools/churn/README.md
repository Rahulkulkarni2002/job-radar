# Customer Churn Prediction

Live app: https://customer-churn-prediction-rahul.streamlit.app/

## At a glance

- **What it does:** predicts which customers of an online retailer will stop buying in the next 90 days, so the business knows who to contact first.
- **Data:** two years of sales, about 804,000 transactions and 5,855 customers.
- **Best model:** Random Forest, chosen after comparing four algorithms. Out of every 100 customers who really stopped buying, it caught about 86.
- **Tested on big spenders:** on a past period, the big spenders it flagged left about 10 times more often than the ones it called safe (46 percent against 5 percent).
- **The result:** a contact list of 292 high value customers, worth about 882 thousand pounds a year, who are most likely to stop buying in the next 90 days.
- **Built end to end:** 10 models tracked in MLflow, a FastAPI endpoint, and a live Streamlit app.

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

**How to read the numbers below:**

- **Accuracy:** out of every 100 customers, how many the model got right, leaving or staying.
- **Recall:** out of every 100 customers who really left, how many the model caught.
- **F1 score:** one score that combines recall with how often the model's flags were right. Closer to 1 is better.
- **AUC:** how well the model puts risky customers above safe ones. 0.5 is a coin flip and 1.0 is perfect.

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

In the end I chose Random Forest as the best model of this first approach, not because it's the most complex option, but because it matched or beat every more complicated alternative, including the ensembles, while being much simpler to actually put into production. That felt like the right tradeoff for a real deployed system rather than chasing a marginal, possibly noisy improvement from added complexity.

## Going further, predicting who will leave next

Everything above uses one snapshot, where the churn label and the features come from the same two year window. That finds customers who have already gone quiet. A business needs to know who is about to leave, so I rebuilt the problem to look forward. I picked a cutoff date, 10 September 2011, which is 90 days before the data ends. Every feature is built only from what happened before that date, and churn means the customer made no purchase in the 90 days after it. That gave me 5,258 customers, and 56.4 percent of them did not buy again in the next 90 days. Because Recency is now measured at the cutoff, before the label period starts, it is a fair feature here and I added it to the same seven features.

**I compared the same four algorithms on this forward looking version, 4,206 customers to train and 1,052 held out to test.**

| Model | Accuracy | Recall | F1 score | AUC |
|---|---|---|---|---|
| Logistic Regression | 74.0% | 80.1% | 0.777 | 0.809 |
| XGBoost | 75.6% | 84.0% | 0.795 | 0.819 |
| Neural Network (MLP) | 75.0% | 83.7% | 0.791 | 0.816 |
| **Random Forest** | **76.2%** | **85.5%** | **0.803** | 0.818 |

**Random Forest was again the best, on accuracy, recall and F1.** In plain words, out of every 100 customers who really stopped buying it caught about 86, and out of every 100 customers it flagged about 76 really left. All four models are close, which told me the features matter more than the choice of algorithm. Without Recency the same Random Forest drops to 72.1 percent accuracy, so Recency is the strongest signal.

### How accurate it is on big spenders

The final result is a list of big spenders at risk, so before trusting it I tested the same method on the past, where the real outcome is known. I copied how the model would really be used. I trained it on an earlier period, with a cutoff of 12 June 2011, then scored every customer at the main cutoff and looked only at the big spenders, the top 25 percent by spend.

| Group | Customers | Really stopped buying |
|---|---|---|
| The 20% of big spenders the model called riskiest | 263 | 122 (46%) |
| The 20% of big spenders the model called safest | 263 | 12 (5%) |

**The big spenders it flagged left about 10 times more often than the ones it called safe.** So the model ranks big spenders by risk well.

### Predicting the next 90 days

The steps above trained and tested the model on a period where the answers were known. The next step uses the model for its real purpose, predicting a period that is not in the data. I trained the final Random Forest on all 5,258 customers, then scored every one of the 5,855 current customers as of the last day of data, 9 December 2011. The model predicts that 3,349 of them, 57 percent, will stop buying in the following 90 days.

### The result in numbers of customers

A list of 3,349 customers is too long to act on, so I narrowed it down. First I ranked all 5,855 current customers by risk and split them into five equal groups.

| Risk group | Customers | Average risk of leaving | Share of last year's spend |
|---|---|---|---|
| Riskiest 20% | 1,171 | 87% | 0.4% |
| High | 1,171 | 74% | 3.9% |
| Middle | 1,171 | 56% | 9.3% |
| Low | 1,171 | 41% | 13.8% |
| Safest 20% | 1,171 | 14% | 72.6% |

The riskiest customers overall spend very little, so they are not where the money is. So I looked only at the customers who spend the most. I kept the top 25 percent of current customers by spend, which is 1,464 high value customers bringing in 85.2 percent of the spend, then ranked those by risk and took the riskiest 20 percent.

**That gives 292 high value customers, who spent about 882 thousand pounds in the last 12 months. They are the list a business would contact first.** Their average risk of leaving is 48.5 percent, against 4.1 percent for the safest high value customers.

These predictions cannot be checked, because the data ends there. The evidence for trusting them is the test on big spenders above, where the customers flagged the same way left about 10 times more often than the ones the model called safe.

## Experiment tracking

I used MLflow to track all ten models I trained, the six from my first approach and the four forward looking ones, logging the parameters, accuracy, precision, recall, and F1 score for each one, along with saving the actual trained model files. I ran into a couple of real environment issues along the way, MLflow initially refused to save the XGBoost and neural network models because of a security check on untrusted object types, which I resolved by using XGBoost's own dedicated logging function and explicitly marking the specific internal types as trusted. I also had the MLflow web dashboard fail to show my logged runs for a while, which turned out to be a mismatch between where the tracking data was actually saved and where the dashboard was looking, not a problem with my actual training code. I confirmed this directly using MLflow's Python client rather than just trusting the browser, and found all my runs were genuinely saved correctly the whole time.

## Building the API

I built a FastAPI application that trains the forward looking Random Forest once when the server starts, then exposes a predict endpoint that takes in a customer's Frequency, Monetary, Tenure, and Recency, calculates the same engineered features used in training, and returns both a churn prediction and the probability that the customer stops buying in the next 90 days. I added input validation so that invalid input, like a Frequency of zero which would cause a divide by zero error when calculating average order value, returns a clean error message instead of crashing the server. I tested this using FastAPI's automatic interactive documentation page and confirmed both the validation and the actual predictions work correctly.

## The deployed app

For the live, publicly deployed version, I built a self contained Streamlit application rather than running the API and the interface as two separate connected services. It uses the same forward looking Random Forest as the notebook and the API. The model is trained once and cached using Streamlit's caching decorator, so it doesn't retrain on every single interaction. Someone visiting the live app can type in a customer's order count, total spend, tenure, and days since their last order, click a button, and immediately see how likely that customer is to stop buying in the next 90 days.

I made this choice deliberately after thinking about whether I actually needed two separate running services for this to be a real, legitimate applied ML project. The FastAPI version still exists in this repository and demonstrates that I can build a real API that other software could call, but for the version anyone can actually visit and use right now, a single self contained app was simpler to deploy and just as complete from a user's perspective.

## What I'd do differently with more time

I would train on several cutoff dates across the year and add seasonal features, since buying patterns change between summer and the weeks before Christmas. I would also wait for the next 90 days of data and check how many of the 292 customers on the contact list really did stop buying. After that I would test whether features like product categories or country give the more complex models a real advantage over Random Forest. I would also connect the deployed app to the MLflow tracked model files instead of retraining at startup, since that is closer to how a real production system works.

## How to run this yourself

To run the notebook, download this repository, open a terminal in its folder and install the packages with `pip install -r requirements-notebook.txt`. Then open `churn.ipynb` in Jupyter or VS Code and choose Run All. The data files are included, so nothing else needs downloading, and the whole notebook runs in under a minute.

To run the app on your own computer, install the packages with `pip install -r requirements.txt` and start it with `streamlit run streamlit_app.py`. To run the API, also install fastapi and uvicorn, then start it with `uvicorn main:app --reload` and open http://127.0.0.1:8000/docs to try it.

## Files in this repository

churn.ipynb contains the full analysis. Part 1 is my first approach. Part 2 trains the forward looking model, tests it on big spenders, predicts the next 90 days for current customers, shows the result in numbers of customers, and tracks the models in MLflow.

main.py is the FastAPI application serving the forward looking model, meant to be run locally with uvicorn.

app.py is the original two service version of the Streamlit app that calls the FastAPI endpoint over the network, kept here to show that architecture works.

streamlit_app.py is the self contained version actually deployed live, with the forward looking model built directly into the app.

requirements.txt lists the Python packages the live app needs, and requirements-notebook.txt lists the ones needed to run the notebook.

cleaned_retail.csv and rfm_table.csv are the underlying cleaned dataset and RFM feature table, reused from the companion segmentation project.

## Tools and skills used

Python, pandas, numpy, scikit learn, XGBoost, MLflow, FastAPI, Streamlit, and Streamlit Community Cloud for deployment.
