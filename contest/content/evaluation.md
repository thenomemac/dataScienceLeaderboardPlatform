## Evaluation
(Your contest evaluation can go here, sample shown below)

The contest consists of predicting whether or not a passenger survived. The leaderboard score will be calculated by root mean squared error: `(Y_hat - Y)**2`

Put another way you could write could define the loss function in python with numpy:

```python
def mse_loss(y, yhat):
    return np.mean((yhat - y)**2)
```

Or in mathematical Notation: $(\hat{y} - y)^{2}$

More text here..
