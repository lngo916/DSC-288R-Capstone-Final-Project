# Temporal Feature Handling Summary for Steam Churn Analysis

## 1. Core Mental Model

For churn prediction, the model should learn from the past to predict the future.

Your raw Steam dataset has many review-level rows:

```text
author_steamid | appid | timestamp_created | review | voted_up | votes_up | comment_count | playtime ...
```

But the churn modeling dataset should usually be transformed into a user-level snapshot table:

```text
author_steamid | features built from data before T | churn label built from data after T
```

So the final machine learning table is not the original raw review table. It is an engineered table where each row represents:

```text
one user at one cutoff time T
```

---

## 2. Feature Cutoff `T`

`T` is the time boundary where you stop observing user behavior for feature construction.

Only data at or before `T` should be used to create model input features.

```text
Data <= T
    → allowed for features
```

Example features from data before `T`:

```text
n_reviews_before_T
n_games_reviewed_before_T
avg_review_length_before_T
positive_review_rate_before_T
total_votes_up_before_T
avg_comment_count_before_T
days_since_last_review
days_since_last_play
```

---

## 3. Label Window

The label window is not a feature.

It is also not gibberish.

It is the future period after `T` used to define the target label.

For example:

```text
T = January 1
label_window_days = 30
label window = January 1 to January 31
```

The label window answers:

```text
Did the user return within 30 days after T?
```

In code, this may look like:

```python
horizon_days = 30
label_end_ts = cutoff_ts + horizon_days * 86400
```

A clearer name would be:

```python
churn_horizon_days = 30
```

or:

```python
label_window_days = 30
```

---

## 4. Feature Window vs. Label Window

For one churn snapshot:

```text
Past behavior                         Future outcome
FEATURE WINDOW                        LABEL WINDOW
-------------------------|-------------------------------|-----------
                         T                              T + 30
                   feature cutoff                    label window end
```

The rule is:

```text
Data at or before T:
    used to build features

Data after T and before/equal T+30:
    used to build the target label

Data after T+30:
    ignored for this specific 30-day churn label
```

---

## 5. What Happens After `T + 30`?

For a 30-day churn label, data after `T + 30` is normally ignored for that specific snapshot.

Example:

```text
T = January 1
T + 30 = January 31
User returns February 10
```

For a 30-day churn definition:

```text
returned_in_30d = 0
churn = 1
```

The user returned eventually, but not within the 30-day horizon. So they are considered churned for this particular label definition.

---

## 6. Columns Do Not Automatically Become Features or Targets

A column itself is not a feature or a target by nature.

Instead, the same raw column can be used differently depending on the time window.

Example with `timestamp_created`:

```text
timestamp_created <= T:
    helps create features like n_reviews_before_T or days_since_last_review

T < timestamp_created <= T+30:
    helps create target like returned_in_30d

timestamp_created > T+30:
    ignored for this snapshot
```

Example with `review`:

```text
review rows before T:
    can create avg_review_length_before_T

review rows inside T to T+30:
    should not be used as features
    can only indicate that the user returned

review rows after T+30:
    ignored for this snapshot
```

---

## 7. Do Not Use Future-Window Review Data as Features

For rows inside `(T, T + 30]`, do not use these as model features:

```text
review
voted_up
votes_up
comment_count
review_length
```

Those rows are future information relative to cutoff `T`.

They should only help answer:

```text
Did the user return during the label window?
```

Bad idea:

```text
Use review text from T+10 to predict whether the user returned by T+30.
```

That leaks the answer because seeing a review at `T+10` already tells you the user returned.

---

## 8. Final ML Table Structure

The model still receives both features and target.

```text
X = features from historical data before T
y = churn label from future data after T
```

A good final churn table might look like:

```text
author_steamid
n_reviews_before_T
n_games_reviewed_before_T
avg_review_length_before_T
positive_review_rate_before_T
total_votes_up_before_T
avg_comment_count_before_T
days_since_last_review
days_since_last_play
churn
```

Where:

```text
feature columns:
    built from rows where timestamp_created <= T

churn:
    built from rows where T < timestamp_created <= T + 30
```

---

## 9. Why Aggregation Is Normal

The raw Steam dataset has one row per review event.

But churn prediction usually predicts whether a user will stop being active.

Therefore, the prediction unit becomes:

```text
one user snapshot
```

not:

```text
one review row
```

So you transform:

```text
many raw review rows
        ↓
one user-level supervised ML row
```

This is normal in churn analysis.

Examples from other domains:

```text
Retail:
    raw purchases → customer-level RFM features → churn

Telecom:
    raw calls/usage/payments → customer-level usage features → churn

Steam:
    raw reviews/playtime behavior → user-level activity features → churn
```

---

## 10. One Snapshot Per User vs. Multiple Snapshots

### One snapshot per user

This means:

```text
one user → one training example
```

Pros:

```text
simpler
less leakage risk
easier to explain
good for first project version
```

Cons:

```text
fewer training rows than raw review rows
only observes each user at one time point
```

### Multiple snapshots per user

This means:

```text
user_1 at T1
user_1 at T2
user_1 at T3
```

Pros:

```text
more training examples
can learn how churn risk changes over time
```

Cons:

```text
more complex
higher leakage risk
train/test split becomes harder
same user snapshots are correlated
```

Recommended project path:

```text
Version 1:
    one snapshot per user
    one global cutoff T
    one label window, such as 30 days

Version 2, only if time allows:
    multiple rolling snapshots per user
```

---

## 11. Recommended Naming

Instead of vague names like:

```python
label_window
```

Use clearer names:

```python
churn_horizon_days = 30
label_window_days = 30
feature_cutoff_ts = T
label_end_ts = feature_cutoff_ts + churn_horizon_days * 86400
```

This makes the code easier to understand.

---

## 12. Clean Rule to Remember

```text
Use the past to describe the user.
Use the future window to define the label.
Never use the future as an input feature.
```

Or even shorter:

```text
Features before T.
Label after T.
Ignore after T + horizon for this snapshot.
```
