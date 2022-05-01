"""
This code creates inputs for purchased power price by using estimated energy charge data


Note: You will need to think of how to connect this code with the code calculating energy charge
      It is becuase in the future, you may need to update the energy charge again with newer brent crude oil futures prices
      or implied volatility.
"""

import pandas as pd
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


#optain current directory
cur_path = os.getcwd()

#path to raw data
loc_of_org_data = os.path.join(cur_path + "/raw_inputs/")

#set location where you will save processed data
path_to_save = os.path.join(cur_path + "/processed_inputs/")

discount = 0.02
base_year = 2019
#load estimated energy charge
#EC = pd.read_csv(loc_of_org_data + "EC_20190827.csv", skiprows=3)
#EC['time1'] = pd.to_datetime(EC['time'], format='%b-%Y') #generate time variable

EC = pd.read_csv(loc_of_org_data + "energy_charge_w_wo_utility_pv.csv")
EC['day'] = 1
EC['time1'] = pd.to_datetime(EC[['year', 'month', 'day']]) #generate time variable


#load timepoints inputs
#read 'timepoints' file from orginal folder
timepoints = pd.read_csv(loc_of_org_data + "timepoints.tab", sep='\t')

#generate year and month variables
timepoints['time']= pd.to_datetime(timepoints['timestamp'], format='%Y%m%dH%H%M')
timepoints['year'] = timepoints['time'].dt.year
timepoints['month'] = timepoints['time'].dt.month
timepoints['day'] =1
timepoints['time1'] = pd.to_datetime(timepoints[['year','month', 'day']])


#merge EC and timepoints variables
EC = pd.merge(EC, timepoints[['time1', 'timepoint_id']], left_on=['time1'], right_on=['time1'], how='left')



#save purchase_power_price input file
list1 = ['high', 'mid', 'low']
list2 = ['EIA', 'brent', 'brent_lb']
#Case: PSIP + 900 MW RFP + 40 MW in each year
for scen1, scen2 in zip(list1, list2):
    EC['purchase_power_price'] = EC['f_ec_'+ scen2 + '_noPV_p']*10
    EC1 = EC[['timepoint_id', 'purchase_power_price']]
    EC1 = EC1.round({'purchase_power_price':4}) #limit the decimal points
    EC1.to_csv(path_to_save + 'power_price_timepoint_'+ scen1 +'.csv', index=False)
#Case: Optimization transition scenario (the results of the Oahu model)
for scen1, scen2 in zip(list1, list2):
    EC['purchase_power_price'] = EC['f_ec_'+ scen2 + '_noPV_opt']*10
    EC1 = EC[['timepoint_id', 'purchase_power_price']]
    EC1 = EC1.round({'purchase_power_price':4}) #limit the decimal points
    EC1.to_csv(path_to_save + 'power_price_timepoint_'+ scen1 +'_opt.csv', index=False)


######################
#Graph
#Graph: trend of averge monthly electricity bill
########################
list = ['f_ec_EIA_noPV_p', 'f_ec_brent_noPV_p','f_ec_brent_lb_noPV_p',
    'f_ec_EIA_noPV_opt', 'f_ec_brent_noPV_opt','f_ec_brent_lb_noPV_opt',]
EC1 = EC.groupby('year')[list].mean().reset_index()

#covernt from nominal to real for the graph

for var in list:
    EC1[var] = EC1[var]/((1 + discount)**(EC1['year']- base_year))


plt.rcParams["figure.figsize"] = (9,6) #set the size of figure
fig, ax = plt.subplots()
ax.plot(EC1['year'], EC1['f_ec_EIA_noPV_opt'],color='orange')
ax.plot(EC1['year'], EC1['f_ec_brent_noPV_opt'],color='blue')
ax.plot(EC1['year'], EC1['f_ec_brent_lb_noPV_opt'],color='green')
ax.set_ylabel('2019 cents/kWh')
ax.set_xlabel('Year')
#get rid of decimal points on x-axis label
ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
ax.set_xlim(2019,2043)
ax.set_ylim(2,17)
ax.spines['top'].set_color('None') #remove line on the top of figure
ax.spines['right'].set_color('None') #remove line on the right of figure
ax.text(2039.5, 11, 'with high oil \n price scenario', fontsize=12, color="orange")
ax.text(2039.5, 6, 'with mid oil \n price scenario', fontsize=12, color="blue")
ax.text(2039.5, 4.5, 'with low oil \n price scenaio', fontsize=12, color="green")


plt.rcParams["figure.figsize"] = (9,6) #set the size of figure
fig, ax = plt.subplots()
ax.plot(EC1['year'], EC1['f_ec_EIA_noPV_p'],color='orange')
ax.plot(EC1['year'], EC1['f_ec_brent_noPV_p'],color='blue')
ax.plot(EC1['year'], EC1['f_ec_brent_lb_noPV_p'],color='green')
ax.set_ylabel('2019 cents/kWh')
ax.set_xlabel('Year')
#get rid of decimal points on x-axis label
ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
ax.set_xlim(2019,2043)
ax.set_ylim(2,17)
ax.spines['top'].set_color('None') #remove line on the top of figure
ax.spines['right'].set_color('None') #remove line on the right of figure
ax.text(2039.5, 11, 'with high oil \n price scenario', fontsize=12, color="orange")
ax.text(2039.5, 6, 'with mid oil \n price scenario', fontsize=12, color="blue")
ax.text(2039.5, 4.5, 'with low oil \n price scenaio', fontsize=12, color="green")
plt.savefig(cur_path + "/../graphs_for_report/energy_charge.pdf")


#keep necessary variables and save them to the processed_inputs folder
#list=['high', 'mid', 'low']
#scenario: EIA (high)
#for scen in list:
#    EC['purchase_power_price'] = EC['EC_'+scen]*10
#    EC1 = EC[['timepoint_id', 'purchase_power_price']]
#    EC1 = EC1.round({'purchase_power_price':4}) #limit the decimal points
#    EC1.to_csv(path_to_save + 'power_price_timepoint_'+ scen +'.tab', sep='\t', index=False)


#scenario: futures price (mid)
#scenario: 1sd lower from futures price (low)
