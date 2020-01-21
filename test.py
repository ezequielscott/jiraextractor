import pandas as pd

df = pd.read_csv('issues.csv')
ch = pd.read_csv('changelog.csv')

print(df[['creator','reporter','assignee']])
print(ch)