# Labeling Fan-Generated Roleplaying Game (RPG) Content: An NLP Task
This project began as a single weekend project completed for my COMP_SCI 349 (Machine Learning) course at Northwestern University.
Students were offered the choice of a number of fixed toy datasets and tasks to complete. I chose to perform multi-label classification based on a custom-generated dataset.

## Data Sources / Fan-Made RPG Content
A list of Reddit posts (comments or primary submissions) containing links two websites ([Homebrewery](homebrewery.naturalcrit.com) or [GMBinder](gmbinder.com)) was obtained using a command-line tool built ontop of the Python Reddit API (PRAW) by myself [located here](https://github.com/nkuehnle/praw-codials). Some processing of the specific web URLs collected via Reddit is provided by functions which live in `./src/scraping.py` and `./src/preprocessing/text_cleaning.py`

4-5k Reddit posts were eventually collected (the initial dataset was close to 2.5-3K at the time of my COMP SCI final). Out of these, around 3K unique pieces of fan-made content were eventually obtained.

Overall, it's worth noting that class-imbalance is heavy within this dataset, so weighted sampling/training methods are utilized in Part 3 for model fitting.

### Data / Model Availability
This repo expects/creates a `./data` folder which contains data and intermediates for different stages. The final size of this folder, with all check-points is around 1.7 GB, so it is not provided here.
All the basic inputs/intermediates used in these notebook are provided on a separate Google Drive folder [here](https://drive.google.com/drive/folders/1ORpfjjJTjaTWUFI6DquHMQhqIT8v9k2B?usp=sharing). This includes a pickled version of the pickled SVC/sklearn model and a .pth file from the trained RoBERTA model. Note that version 1.2.2 of sklearn was used for this (see requirements.txt) 

## Original Project
To reduce redundancy/ambiguity, the original copy of my COMP_SCI 349 (Machine Learning) final has been privated. The PDF write-up I submitted for that project has been provided in `./OLD_COMP_SCI_349_NK_Final.pdf` if you're curious to see how the data looked back then.
