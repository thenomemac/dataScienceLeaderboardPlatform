# Data Science Leaderboard Platform
This flask app implements similar functionality to Kaggle.com. The app allows companies/individuals to host their own data science competitions with a common task framework leader board and automatic scoring.

Note that this app provides the functionality for users to create logins, then a user can upload a submission file. This submission file is scored agains a public and private leaderboard holdout dataset. This is the well know predictive modeling competion format established by kaggle.com. Anyone can access the app without a login and view the public leaderboard. Only the contest admin can view the private leaderboard until the contest submission deadline has past. Then the score on the leaderboard is the joint public/private holdout score.

The app also provides the functionaly to have serveral web pages for your predictive modeling contest:
* Description
* Evaluation
* Rules
* Prizes
* Timeline
* Discussion 
  * Implemented via link: twitter, reddit, sharepoint, ext
* Leader Board
  * Implemented in javascript
  * Shows most recent submission by user


Steps to running the app:

1. Check *./config.py* and make sure the ENVIRONMENT variables make sense.
  * Note that many files feature `#! flask/bin/python` so you can run them with a python virtualenv in the project directory or you can use you current python distribution.
2. To launch the app run with your default python distribution: `python run.py`

