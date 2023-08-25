# Predicting content labels for fan-made roleplaying game (RPG) content
This project began as a single weekend project completed for my COMP_SCI 349 (Machine Learning) course at Northwestern University.
Students were offered the choice of a number of fixed toy datasets and tasks to complete. I chose to perform multi-label classification based on a custom-generated dataset.

## Data Sources
A list of Reddit posts (comments or primary submissions) containing links two websites (described below) was obtained using a command-line tool built ontop of the Python Reddit API (PRAW) by myself [located here](https://github.com/nkuehnle/praw-codials), some processing of the specific web URLs collected via Reddit is provided by functions which live in /src/scraping.py and /src/preprocessing/text_cleaning.

4-5k Reddit posts were eventually collected (the initial dataset was close to 2.5-3K at the time of my COMP SCI final. Out of these, around 3K unique pieces of content were eventually obtained.
