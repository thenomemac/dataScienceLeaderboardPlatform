# Data Science Leaderboard Platform
This flask app implements similar functionality to Kaggle.com. The app allows companies/individuals to host their own data science competitions with a common task framework leader board and automatic scoring.

Note that this app provides the functionality for users to create logins, then a user can upload a submission file. This submission file is scored agains a public and private leaderboard holdout dataset. This is the well know predictive modeling competion format established by Kaggle.com. Anyone can access the app without a login and view the public leaderboard. Only the contest admin can view the private leaderboard until the contest submission deadline has past. Then the score on the leaderboard is the joint public/private holdout score.

The app also provides the functionally to have several web pages for your predictive modeling contest:
* Description
* Evaluation
* Rules
* Prizes
* Discussion 
  * Implemented via link: twitter, reddit, sharepoint, ext
* Leader Board
  * Implemented in javascript
  * Shows most recent submission by user


Steps to running the app:

1. Edit the configuration in the `leaderBoardApp.py` file or export an `LEADERBOARDAPP_SETTINGS` environment variable pointing to a configuration file.
2. Edit the modeling contest specific settings in `leaderBoardApp.py`
3. Edit the markdown files documenting the contest rules and more in `contest/content`
4. Edit the function used to score and load user submitted data with the loss function for the contest in `contest/helperfxns/__init__.py`
5. Place any files used in scoring in `contest/data` and any files the user needs to download in `contest/download`
6. Run a `mkdir ./contest/submissions/` cmd to create the ignored folder where user uploads are cached. Or change global variable to save uploads to alternate path.
7. By default `init_db()` at the bottom of the `leaderBoardApp.py` will only run if the database `./dsLeaderboard.db` does not exist
8. To launch the app run with your default python distribution: `python leaderBoardApp.py`

Note that the License is stated as MIT. This only pertains to app specific code. In the `static/` path copies of MathJax, jquery and bootstrap JS are included for making the app self contained. These dependencies have their own license agreements.

Is the app tested? No unit tests still need to be written.
