# Week 1 — Dataset Selection and Problem Definition

## Problem Faced

So we started this project thinking it would be straightforward we would grab a dataset, train an autoencoder, done. But in two days it turned out to be one of the most basic cybersecurity datasets like HDFS or BGL or Thunderbird which are basically just system logs. They track server crashes and disk failures, not what actual users are doing on a network. We needed user behavior logins, emails, file copies, web browsing and none of those datasets had it. Also our proffessor made it pretty clear during the first check-in that "by just applying deep learning to logs" wasnt going to fly as a project topic, unless we found something actually new.

## Relevant Context

We spent most of the week just downloading needfull files and opening it and realizing it was useless. Like some of the datasets had no labels, so even if something weird was happening in there we would have no way of knowing if we actually caught it or not. Others were so stripped down they were basically just timestamps with no user ID attached like how do you do behavioral analysis if you dont know which user did what? We also looked at what commercial SIEM tools are doing these days and realized the baseline is already pretty high, most of them already do some kind of anomaly scoring so we couldnt just build another one.

## Key Observation

The thing that actually helped was when we stopped searching for "log dataset" and started searching specifically for insider threat data. That narrowed things down a lot and we found the CERT Insider Threat Test Dataset. It was complete actually had all the event types we wanted  logon, file, HTTP, device, email  and theyre all linked to actual users with known malicious scenarios. Around the same time we realized our novelty wasnt going to come from just picking a fancier model. It had to come from how we used it. We needed to actually solve problems that existing work doesnt handle well  like explaining why something is anomalous instead of just giving a score, dealing with new users who dont have much history, and actually comparing architectures instead of just picking one and claiming its the best.

## Solution

So we decided to go with CERT as our main dataset. And we mapped out three things that would make our project different from just another anomaly detector: Explainability so analysts actually know what triggered the alert.
Transfer learning to handle the cold start problem where a new user has almost no history
Proper comparison between LSTM/GRU, Transformer, and a hybrid of both instead of just picking whichever one we liked more.

## Outcome

By the end of the week we had a path paved and project went from "build an anomaly detector" to "build and compare explainable transferable anomaly detectors on actual user behavior data."

# Week 2 — Handling and Preprocessing Large-Scale Heterogeneous Data

## Problem Faced

CERT seemed great when we read about it. Then we actually opened the files and it was a mess. The data is split across like five or six huge CSV files and every single one has a different structure. Logon events have columns that file events dont have. Emails use a different timestamp format than HTTP logs. Just trying to get one users events in chronological order took way longer than it should have. Also we quickly realized we couldnt just load everything into pandas at once, the full dataset is massive and would crash our laptops. And even if we fixed the memory problem, raw logs are just individual events. Our models need sequences of behavior, not random rows. So we had to figure out how to turn all these scattered log entries into actual user sessions that a neural network could understand.

## Relevant Context

We tried some dumb things first. Like literally concatenating all the CSVs and sorting by timestamp which just created this horrible mixed-schema table where most cells were empty. Then we tried one-hot encoding every column we saw which made the feature space enormous and basically all zeros. We also messed up our first train-test split because we didnt separate the labels early enough some user IDs and timestamps leaked information between train and test and we had to throw the whole thing out and start over.

## Key Observation

What actually clicked was when we stopped treating this like "just clean the data" and started thinking about it as building a pipeline that produces a very specific output format. We needed one unified event representation that every source could map into. We needed to process files in chunks so we werent holding gigabytes in RAM. And we needed sessionization grouping a users events into logical sessions because thats the bridge between raw logs and the sequential input our models actually need.

## Solution

We built a pipeline that handles each CERT source separately first. It picks out only the columns we actually care about, normalizes the timestamps into one format, then merges everything into a single chronological event stream per user. From there it groups events into sessions and encodes the features into a fixed vector that the neural nets can eat. We wrote it to process in chunks and save intermediate files so the heavy raw-data processing only happens once. And labels are kept completely separate until evaluation no more leakage.

Raw CERT logs → Unified events → Sessionization → Feature encoding → Behavioral sequences → Model input

## Outcome

We finally got from raw scattered logs to clean sequential data. More importantly we now have one preprocessing pipeline that feeds all three models the same way — same format, same session logic, same encoding. So when we compare the architectures later it will actually be a fair comparison.

# Week 3 — Model Architecture Selection and Experimental Design

## Problem Faced

Okay so now we had clean data and we just stared at it for a while because we had no idea which model to build. LSTM and GRU are the obvious choice for sequences everyone uses them, they are easy to understand, lots of examples online. But Transformers are everywhere now and self-attention should theoretically catch long-range patterns better than recurrence. Then we started wondering if we were forcing a choice that didnt need to exist maybe a hybrid that uses LSTM for local patterns and attention for global dependencies would be better than both? We didnt want to just pick one based on a gut feeling. We also had to figure out evaluation. In security datasets anomalies are super rare so accuracy is basically meaningless a model that says everything is normal gets like 99% accuracy and is completely useless.

## Relevant Context

We spent a lot of time just arguing about this. LSTMs are stable and train fast but they might miss stuff where an event from the morning predicts something suspicious in the afternoon. Transformers can see those long connections but they might overfit on shorter sequences and they take longer to train. For evaluation we looked at how real SIEM products are actually judged in industry and its not just detection rate its false positives because alert fatigue is a real problem, and inference speed because nobody wants a detector that takes ten seconds per event.

## Key Observation

Instead of trying to prove that one architecture is the best, we should just build all three under the exact same conditions and let the numbers decide. That automatically makes the project more rigorous. For metrics F1-score actually handles the class imbalance problem unlike accuracy. And tracking false positive rate plus training time plus inference latency gives a much more realistic picture of whether any of this is actually deployable. We also decided to formalize the transfer learning idea pretrain a generic model on all users together then finetune on individual users with limited data. Wed test it at day 5 day 10 and day 20 of available history to see if it actually helps with cold start. And for explainability we would pull attention weights from the Transformer and hybrid models to highlight which specific events in a sequence looked suspicious so the analyst gets an explanation not just a number.

## Solution

So heres what we settled on:

1. *LSTM/GRU Autoencoder* — the baseline, simple sequential detector.
2. *Transformer Autoencoder* — uses self-attention to catch long-range dependencies.
3. *Hybrid LSTM + Attention* — combines both approaches.

All three get the same preprocessed input and the same train-test split. Primary metric is F1-score plus we track false positives training time and latency. Transfer learning experiments are part of the plan from the start. And attention visualization drives the explainability part.

## Outcome

We stopped arguing about which model is best and committed to running the experiment properly. The project is now an actual empirical comparison with transfer learning and explainability built in from the beginning instead of being things we might add later if we have time.
