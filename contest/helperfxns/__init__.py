import numpy as np
import pandas as pd

def score(yhat, y):
    return float(np.mean((yhat - y)**2))

#note that if an error is thrown in this fxn 
#then the user will get a flash() that upload failed
def loadAndScore(fullPath):
    """function loads the dataset from filePath and scores submission
    against the solution file
    function returns tuple in format public, private, total loss function score"""
    #in a real implementation of this app add more QA in this fxn
    sub = pd.read_csv(fullPath)
    ans = pd.read_csv('contest/data/submissionSolution.csv')
    public_score = score(sub.Survived[ans.PublicLeaderboardInd == 1],
                         ans.Survived[ans.PublicLeaderboardInd == 1])
    private_score = score(sub.Survived[ans.PublicLeaderboardInd == 0],
                         ans.Survived[ans.PublicLeaderboardInd == 0])
    total_score = score(sub.Survived,
                         ans.Survived)
    return (public_score, private_score, total_score)

