"""
This code generates the PPA price schedule of PV at UH
"""
import pandas as pd
import matplotlib.pyplot as plt
import os


#Set directory for original inputs and process outputs
cur_path = os.getcwd() #obtain the current working directory
print(cur_path)

path_to_org_data = os.path.join( cur_path, 'original_inputs/')
path_to_save = os.path.join(cur_path, 'processed_inputs/')

#set ppa_price is 17 cents per kWh
PPA = 17
#inflation rate
r = 0.02

#load original PPA dataset
PPA_price = pd.read_csv(path_to_org_data + "ppa_price_timepoint.tab", sep="\t")
PPA_price.head(2)
#add timepoints.tab
timepoints = pd.read_csv(path_to_org_data + "timepoints.tab", sep="\t")

#merge PPA_price and timepoints
PPA_price = pd.merge(PPA_price, timepoints, left_on = "timepoint_id", right_on="timepoint_id",
    how='left')

#generate year variable
PPA_price['year'] = PPA_price['timestamp'].apply(str).str[0:4]
PPA_price['year'] = pd.to_datetime(PPA_price.year, format = '%Y').dt.year

#Convert PPA price from nominal to real by using 2% interest rates
PPA_price['ppa_price'] = PPA
for y in range(2019, 2039, 1):
    PPA_price.loc[(PPA_price['year']>y) & (PPA_price['year'] <=y+1),
        'ppa_price'] = PPA_price['ppa_price'] /((1 + r) ** (y-2019))
PPA_price['ppa_price'] = PPA_price['ppa_price']*10




fig, ax=plt.subplots()
ax.plot(PPA_price['year'], PPA_price['ppa_price'])

PPA_price = PPA_price[['GENERATION_PROJECT', 'timepoint_id', 'ppa_price']]

#save the file into the processed_inputs
PPA_price.to_csv(path_to_save + "ppa_price_timepoint.tab", sep="\t", index=False)
