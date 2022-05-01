"""
This script generates energy charge, non-energy charge, demand charge, PPA,
and amortized costs by using the outputs of the UH-switch model.

The model includes the green tariff project and virtual rider option

The sctipt generates following figures
1) A line graph showing future monthly bill trend from 2020-2039
2) A area graph illustrating the structure of the UH bill from 2020-2039
4) A hourly load balance figure of the peak demand day (2035, May 11)
5) A pie chart presenting the presentage of generation sources used to generate electricity in 2039
6) A table showing capacity built in each investment period

Use terminal to run this code. Type following command where this code is located
'python prepare_final_results_1.py 10L_EC1_NEC0_PV0_PPA0_CG0_GT1_VRM1'

This code uses gen_take_or_pay_cost as PPA.

Last day of revision: Jun 29 2020

"""


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os
import os.path
import numpy as np
import argparse
from os import rmdir
import shutil

from matplotlib.dates import DateFormatter
from matplotlib.dates import HourLocator
from matplotlib import dates



#Set a current directory
cur_path = os.getcwd() #obtain the current working directory


######
#set an option for preparing outputs

parser = argparse.ArgumentParser(description = 'Prepare outputs')
parser.add_argument('indir', type=str,
    help='Add the name of output folder. Ex) python prepare_final_reulsts_4.py EM0_00L_EC1_NEC0_PV0_PPA0_CG0_WO0_VRM0'
    )

args = parser.parse_args()
#print("Preparing outputs = {}".format(args.indir))
output = args.indir

######


print("=" *50)
print("Prepare final results (graphs and table)")
print("Scenario = {}".format(args.indir))
print("=" *50)

#Set the path of the outputs used.
#output = "EM0_00L_EC1_NEC0_PV0_PPA0_CG4_WO1_VRM0"
path_to_outputs = os.path.join(cur_path + "/" + output + "/")
path_to_inputs = os.path.join(cur_path + "/inputs_" + output)
path_to_CapFac = os.path.join(cur_path + "/processed_inputs/" )

##############################################################
#load cost_period
# Obtain amortized costs and demand charge
##############################################################

file_name = "cost_period.csv"
costp = pd.read_csv(path_to_outputs + file_name)
costp['year'] = costp['period']
invyears = 5



#add variable 'EmissionsCosts' or 'AmortizedCost' if not exist
list = ['AmortizedCost', 'EmissionsCosts']
for var in list:
    if not var in costp.columns:
        costp[var] = 0

#create the same 'costp' for each year and append it
costpj = pd.DataFrame()
for i in range(1,5):
    tab = costp.copy()
    tab['year'] = tab['year']+i
    costpj=costpj.append(tab, ignore_index=True)
    del(tab)

costp = costp.append(costpj, ignore_index=True)
costp = costp.sort_values(by='year')


#create AmortizedCost and DemandCharges
costp['AmortizedCost'] = costp['TotalGenFixedCosts']/invyears/12
costp['DemandCharges'] = costp['DemandCharges']/invyears/12
costp['EmissionsCosts'] = costp['EmissionsCosts']/invyears/12
#keep year, AmortizedCost and DemandCharges
costp = costp.loc[:,['year', 'AmortizedCost', 'DemandCharges', 'EmissionsCosts']]
costp = costp.reset_index(drop=True)

#########################################
# Generate EnergyCharge, PPACost, NonEnergyCharge
# Start to work on cost_ts.txt file
#########################################

file_name = "cost_ts.csv"
costm = pd.read_csv(path_to_outputs + file_name)


#rename GenTakeOrPayCosts to PPACost
costm = costm.rename(columns={'GenTakeOrPayCostsInTP':'PPACost'})
costm = costm.rename(columns={'CogenPPACostInTP':'CogenPPACost'})

#Check whether PPA, CogenPPA, and TotalCredit exists or not.
#Then, if not exists, set those variables as 0
list = ['PPACost', 'CogenPPACost']
for var in list:
    if var in costm.columns:
        print("{} exists".format(var))
    else:
        print("{} does not exist".format(var))
        costm[var] = 0

#compute Energy Charge, Fuel costs, PPA costs, and Non-Energy charge by multiplying investment years
costm = costm.loc[:, ['timeseries', 'FuelCostsPerTP', 'PurchasedPowerCost',
    'PPACost', 'NonEnergyCharge', 'CogenPPACost']]
costm['EnergyCharge'] = (costm['PurchasedPowerCost']) * invyears
costm['FuelCost'] = (costm['FuelCostsPerTP']) *invyears
costm['PPACost'] = costm['PPACost'] * invyears
costm['NonEnergyCharge'] = costm['NonEnergyCharge'] * invyears
costm['CogenPPACost'] = costm['CogenPPACost'] * invyears
#Note: EnergyCharge includes both purchased power costs and PPA costs

#sum energy charge and non-energy charge within a month (same as bysort month: egen in STATA)
costm = costm.groupby('timeseries')[['EnergyCharge', 'FuelCost',
    'NonEnergyCharge', 'PPACost', 'CogenPPACost']].sum().reset_index()
costm = costm.rename(columns={'timeseries':'YearMonth'})

#Generate timeseries variable: year, month, day, time
costm['year'] = costm['YearMonth'].apply(str).str[0:4]
costm['year'] = pd.to_datetime(costm.year, format='%Y').dt.year
costm['month'] = costm['YearMonth'].apply(str).str[4:6]
costm['month'] = pd.to_datetime(costm.month, format='%m').dt.month
costm['day'] = 1
costm['time'] = pd.to_datetime(costm[['year','month', 'day']])


#combine information of energy and non-energy charges and amortized costs and demand charge
costtot = pd.merge(costm, costp, left_on = 'year', right_on = 'year',
    how='left')

costtot['YearMonth1'] = costtot['time'].dt.to_period('M')




###############
#Add the value of green tariff credits
#output = "EM0_00L_EC1_NEC0_PV0_PPA0_CG0_WO0_VRM0"

scenario = output[30:33]
if (scenario == "WO0"):
    costtot['TotalCredit'] = 0

else:
    #Run the code that calculate the credit from GreenTariff project

    #GreenTariff_WO.py uses the hourly capacity factor information from NREL
    os.system('python GreenTariff_WO.py {}'.format(output))
    credit = pd.read_csv(path_to_outputs + "GT_Credits.csv")
    costtot= pd.merge(costtot, credit, left_on = 'year', right_on = 'year',
    how = 'left')
    #Set 0 if the value of total credit is not exist
    costtot['TotalCredit'] = costtot.loc[:,'TotalCredit'].fillna(value=0)
#    costtot['PV_Gen'] = costtot.loc[:,'PV_Gen'].fillna(value=0)
    print("The credits from 10MW green tariff project is included")

################


#convert nominal to real for the values from cost_ts.csv
financials = pd.read_csv(path_to_inputs + "/financials.csv")
discount = financials.loc[0,"discount_rate"]

list = ['EnergyCharge', 'NonEnergyCharge', 'FuelCost',
    'PPACost', 'CogenPPACost', 'TotalCredit']
for var in list:
    costtot[var] = costtot[var]/((1+discount)**(costtot['year']-2019))

#TotalCredit is multipled by 1000 since the unit of is already thousand dollars
costtot['TotalCredit'] = costtot['TotalCredit']*1000
#Generate total electricity bill (amortized costs are included)
costtot['TotalEbill'] = (costtot['EnergyCharge'] + costtot['NonEnergyCharge'] +
    costtot['DemandCharges'] + costtot['FuelCost'] + costtot['AmortizedCost'] +
    costtot['EmissionsCosts'] + costtot['PPACost'] + costtot['CogenPPACost'] -
    costtot['TotalCredit']) #add TotalCredits from GreentTariff project


#Drop unnecessary variables
costtot = costtot[["YearMonth", "year", "time", "TotalEbill", "EnergyCharge", "NonEnergyCharge",
    "AmortizedCost","DemandCharges","EmissionsCosts", "PPACost", "FuelCost", "CogenPPACost",
    "TotalCredit"]]


#Export the result as an excel file
costtot.to_csv(path_to_outputs + 'summarycost.csv', index=False, header=True)

print("wrote summarycost.csv")


###################################
###################################
# Constructing Graphs
###################################
###################################

###################################
# Graph 1: The trend of Total Electricity bill
###################################

#Conver the unit of TotalEbill from dollars to thousnd dallars
costtot['TotalEbill'] = costtot['TotalEbill']/1000
costtot.sort_values(by="time")

#obtain annual average of monthly bill
costtot = costtot.groupby('year')['TotalEbill'].mean().reset_index()


#add the results of the status-quo scenario with mid oil prices and PSIP renewable transition scenario
#scenario = output[0:3]
baseline = "baseline/EM0_00L_EC1_NEC0_PV0_PPA0_CG0_WO0_VRM0"


path_to_baseline = os.path.join(cur_path+  "/" + baseline + '/')
b_totbill=pd.read_csv(path_to_baseline + 'summarycost.csv')
b_totbill=b_totbill.groupby('year')['TotalEbill'].mean().reset_index()
b_totbill['TotalEbill'] = b_totbill['TotalEbill']/1000

#add past monthly_average_EBill
past_TEB = pd.read_excel(cur_path + '/processed_inputs/past_monthly_average_TEB_UH.xlsx')


#add baseline2 results (this baseline moves dependin on PSIP, oil prices and HECO's sales)
scenario_EM = output[0:3]
scenario = output[8:16]
base_output = scenario_EM + "_00L_" + scenario + "_PV0_PPA0_CG0_WO0_VRM0"
path_to_baseline2 = os.path.join(cur_path + "/baseline/" + base_output + "/")
b_totbill2=pd.read_csv(path_to_baseline2 + 'summarycost.csv')
b_totbill2=b_totbill2.groupby('year')['TotalEbill'].mean().reset_index()
b_totbill2['TotalEbill'] = b_totbill2['TotalEbill']/1000



#Graph: trend of averge monthly electricity bill
plt.rcParams["figure.figsize"] = (9,6) #set the size of figure

fig, ax = plt.subplots()
line1, =ax.plot(past_TEB['year'], past_TEB['t_elec_cost'], color='black')
line2, =ax.plot(b_totbill['year'], b_totbill['TotalEbill'], '--', color='lightgrey')
line3, =ax.plot(costtot['year'], costtot['TotalEbill'], color='blue')
line4, =ax.plot(b_totbill2['year'], b_totbill2['TotalEbill'], color='dimgrey')
ax.set_ylabel('Thousand 2019 dollars')
ax.set_xlabel('Year')
#get rid of decimal points on x-axis label
ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
ax.set_xlim(1999,2040)
ax.yaxis.set_ticks(np.arange(0, 3500, 500))
plt.yticks(rotation='vertical', va='center')
ax.set_ylim(0, 3500)
ax.spines['top'].set_color('None') #remove line on the top of figure
ax.spines['right'].set_color('None') #remove line on the right of figure
ax.yaxis.grid(color='grey', linestyle=':')
ax.axvline(2020, color='black', linestyle= '--', lw=1)
ax.text(2001, 3200, "Past Bills (Average Monthly)", fontsize=15)
ax.text(2024, 3200, "Projected Future Bills", color='blue', fontsize=15)
ax.axvspan(1999, 2020, facecolor="grey", alpha=0.3)
leg = ax.legend((line3, line4, line2,),
    ('Alternative scenario', 'Status-quo$^1$', 'Status-quo with mid fuel prices & \n PSIP renewable transition'),
    loc=(0.52, 0.03), edgecolor='None',
    facecolor='None', fontsize=12)
#leg = ax.legend((line3, line2,),
#    ('Alternative scenario', 'Status-quo with mid fuel prices & \n PSIP renewable transition'),
#    loc=(0.52, 0.03), edgecolor='None',
#    facecolor='None', fontsize=12)
#Set the color of text in the legend as the same as the line
for line, text in zip(leg.get_lines(), leg.get_texts()):
    text.set_color(line.get_color())
#set the title of figure
plt.title("Average monthly bill", color="blue", fontsize=20)

#save the figure under the output folder
plt.savefig(path_to_outputs + "avg_bill_" + output + ".pdf")
print("The figure presenting future bills is saved under the graphs folder")



########################################################
#Graph2 : The Structure of Monthly Bill
########################################################
summarycost = pd.read_csv(path_to_outputs + "summarycost.csv")

summarycost.head()

#Compute annual average of each variable
list =['TotalEbill', 'EnergyCharge', 'NonEnergyCharge', 'AmortizedCost', 'TotalCredit',
    'DemandCharges', 'PPACost','FuelCost', 'EmissionsCosts' , 'CogenPPACost']
summarycost = summarycost.groupby('year')[list].mean().reset_index()


#Convert to the Thousand dollars
for var in list:
    summarycost[var] = summarycost[var]/1000


fig, ax = plt.subplots()
ax.plot(summarycost['year'], summarycost['TotalEbill'], color='k', linewidth =3 ,label = 'Total Bill')
plt.stackplot(summarycost['year'],
    summarycost['EnergyCharge'] ,
    summarycost['NonEnergyCharge'],
    summarycost['DemandCharges'] ,
    summarycost['PPACost'],
    summarycost['AmortizedCost'],
    summarycost['FuelCost'],
    summarycost['EmissionsCosts'],
    summarycost['CogenPPACost'],
    labels=['Energy charge', 'Non-energy charge', 'Demand charge', 'PPA', 'Amortized cost',
    'Natural gas charge', 'Carbon cost', 'PPA Cogen'],
     alpha=0.8)
ax.legend(loc='upper right', fontsize=11, ncol=3, edgecolor='None')
#ax.legend(loc='upper right', ncol=3, fontsize=9)
ax.set_ylabel('Thousand 2019 dollars')
ax.set_xlabel('Year')
ax.set_ylim(0, 4500)
ax.xaxis.set_major_formatter(ticker.FormatStrFormatter("%d"))
ax.set_xlim(2020,2040)
ax.spines['top'].set_color('None') #remove line on the top of figure
ax.spines['right'].set_color('None') #remove line on the right of figure
#set the title of figure
plt.title("Structure of the Bill", color="blue", fontsize=20)

#save the figure under the output folder
plt.savefig(path_to_outputs + "bill_struc_" + output + ".pdf")




#########################################################
#Graph 3: load balance
#########################################################

#load variable 'load_balance'
load_balance = pd.read_csv(path_to_outputs + "load_balance.csv")

#load variable "dispatch-wide.txt"
dispatch_wide = pd.read_csv(path_to_outputs + "dispatch-wide.csv")


#load the original demand line
org_demand = pd.read_csv(path_to_baseline + "/load_balance.csv")


#generate year, month, date, hour, minute, time and time 1 variables in each datafrme
for df in (load_balance, dispatch_wide, org_demand):
    df['year'] = df['timestamp'].apply(str).str[0:4]
    df['year'] = pd.to_datetime(df.year, format = '%Y').dt.year
    df['month'] = df['timestamp'].apply(str).str[4:6]
    df['month'] = pd.to_datetime(df.month, format='%m').dt.month
    df['day'] = df['timestamp'].apply(str).str[6:8]
    df['day'] = pd.to_datetime(df.day, format='%d').dt.day
    df['hour'] = df['timestamp'].apply(str).str[9: 11]
    df['hour'] = pd.to_datetime(df.hour, format='%H').dt.hour
    df['minute'] = df['timestamp'].apply(str).str[11:13]
    df['minute'] = pd.to_datetime(df.minute, format = '%M').dt.minute
    df['time'] = pd.to_datetime(df[['year','month', 'day']])
    df['time1'] = pd.to_datetime(df[['year', 'month','day','hour','minute']])


#keep data only in 2035
load_balance_2035 = load_balance.loc[(load_balance['year'] == 2035)]
dispatch_wide_2035 = dispatch_wide.loc[(dispatch_wide['year']==2035)]
org_demand_2035 = org_demand.loc[(org_demand['year']==2035)]
#Note: In 2035, the model chooses 3 days for each month for the sampling. But, in 2039, the model
#       chooses only 1 day. To check the loand balance of the peakest day in the year, I chose 2035.


###############
#Add the value of green tariff credits
scenario = output[30:33]
if (scenario == "WO0"):
    load_balance_2035['WO_PV_Gen'] = 0
    print("No Green Tariff")
else:
    #Obtain capacity factor from west oahu
    CapFac_WO = pd.read_csv(path_to_CapFac + "west_oahu_cap_factor.csv")
    #hourly capacity factor information from 2006 to 2015

    #Compute the average of capacity factor of each hour or each date
    CapFac_WO = CapFac_WO.groupby(['month','day','hh'])[['cap_factor']].mean().reset_index()
    # Note that based on calculation, PV in West Oahu generation about 7 hours per day on average
    # This might be somewhat different from our pervious assumption that 5 hours per day generation on average

    CapFac_WO['WO_PV_Gen'] = (CapFac_WO['cap_factor']) * 10
    CapFac_WO['hour'] = CapFac_WO['hh']

    load_balance_2035 = pd.merge(load_balance_2035,
        CapFac_WO[['WO_PV_Gen', 'month', 'day', 'hour']],
        left_on=['month', 'day', 'hour'], right_on=['month', 'day', 'hour'],
        how='left')
    print("Green Tariff included")

################
#Subtract WO_PV_Gen from PurchasePowerZone
load_balance_2035['PurchasePowerZone'] = load_balance_2035['PurchasePowerZone'] -  load_balance_2035['WO_PV_Gen']
#Convert "PurchasedPowerCost" to zero if it is negative
load_balance_2035.loc[load_balance_2035.PurchasePowerZone < 0, 'PurchasePowerZone'] = 0

#-------------------
#option1
#------------------------

#find the date that has the peakest demand of electricity
#And drow the hourly load and supply for that day
peak_day_2035 = load_balance_2035.loc[
    load_balance_2035.groupby(['time'])['zone_demand_mw'].transform(max)
    == load_balance_2035['zone_demand_mw'].max()
    ]

#------------------------
#option2
#-----------------------
#find the date that has the largest daily electricity consumption within the same year
#generated daily toal electricity consumption
#load_balance_2035['daily_mw'] = load_balance_2035.groupby('time')['zone_demand_mw'].transform('sum')


#find the date having the higest consumption
#peak_day_2035 = load_balance_2035.loc[
#    load_balance_2035.groupby(['time'])['daily_mw'].transform(max)
#    == load_balance_2035['daily_mw'].max()
#    ]


#---------------------
#option3
# pick the date manually
#----------------------
#load_balance_2035 = load_balance.loc[(load_balance['year'] == 2035)]
#dispatch_wide_2035 = dispatch_wide.loc[(dispatch_wide['year']==2035)]
#peak_day_2035 = load_balance_2035.loc[(load_balance['month'] ==5)]
#peak_day_2035.head(3)
#merge dispatch_wide_2035 with peak_day_2035

list = ['Cogen_Power_Plant', 'Battery_Storage', 'TotalCoolingElectricityOffset',
    'Rooftop_PV-2020', 'Rooftop_PV-2025', 'Rooftop_PV-2030',
    'Rooftop_PV-2035', 'Rooftop_PV-2020_PPA']
for var in list:
    if var in dispatch_wide_2035.columns:
        print("{} exists".format(var))
    else:
        print("{} does not exist".format(var))
        dispatch_wide_2035.loc[:, var] = 0

peak_day_2035 = pd.merge(peak_day_2035,
    dispatch_wide_2035[['Battery_Storage', 'Cogen_Power_Plant' , 'Rooftop_PV-0',
    'Rooftop_PV-2020', 'Rooftop_PV-2025', 'Rooftop_PV-2030',
    'Rooftop_PV-2035', 'Rooftop_PV-2020_PPA', 'time1']],
    left_on='time1', right_on='time1',
    how='left')



if 'TotalCoolingElectricityOffset' in peak_day_2035.columns:
    print("t")
else:
    peak_day_2035.loc[:,'TotalCoolingElectricityOffset'] = 0


#generate a variable presenting the sum of non-PPA PV generation
peak_day_2035 = peak_day_2035.rename(columns={'Rooftop_PV-2020_PPA': 'PPAZone'})
peak_day_2035['PV'] = (
    peak_day_2035['Rooftop_PV-0'] + peak_day_2035['Rooftop_PV-2020'] +
    peak_day_2035['Rooftop_PV-2025'] + peak_day_2035['Rooftop_PV-2030'] + peak_day_2035['Rooftop_PV-2035']
    )
peak_day_2035['Total_cogen'] = peak_day_2035['TotalCoolingElectricityOffset'] + peak_day_2035['Cogen_Power_Plant']
org_demand_2035 = org_demand_2035.rename(columns ={'zone_demand_mw': 'org_demand'})
#org_demand_2035['org_demand'] = org_demand_2035['zone_demand_mw']
peak_day_2035 = pd.merge(peak_day_2035, org_demand_2035[['org_demand', 'time1']], left_on='time1',
    right_on='time1', how='left')


#https://www.dataquest.io/blog/tutorial-time-series-analysis-with-pandas/
peak_day_2035 = peak_day_2035.sort_values(by='time1')
org_demand_2035 = org_demand_2035.sort_values(by='time1')



#Construct the graph
plt.rcParams["figure.figsize"] = (9,6) #set the size of figure
fig, ax = plt.subplots()
ax.plot(peak_day_2035['time1'], peak_day_2035['org_demand'], color='grey', linewidth=3,
    linestyle = '--', label = 'Org. UH demand')
ax.plot(peak_day_2035['time1'], peak_day_2035['zone_demand_mw'], color='dimgrey', label='UH demand',
    linewidth=5)
plt.stackplot(peak_day_2035['time1'],
    #y-axis
    peak_day_2035['Total_cogen'],
    peak_day_2035['PurchasePowerZone'],
    peak_day_2035['PPAZone'],
    peak_day_2035['PV'],
    peak_day_2035['WO_PV_Gen'],
    peak_day_2035['Battery_Storage'],
    labels=['Cogeneration plant', 'Purchased power','PV with PPA', 'PV',
        'Green Tariff', 'Battery discharge'],
    #colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99'],
    colors=['pink', 'red', 'blue', 'green', 'limegreen', 'orange'],
    alpha=0.8)
majorFmt = dates.DateFormatter('%H:%M')
ax.xaxis.set_major_formatter(majorFmt)
minlocator = dates.HourLocator(byhour=[0, 8, 16, 24])  # range(60) is the default
ax.xaxis.set_major_locator(minlocator)
ax.spines['top'].set_color('None') #remove line on the top of figure
ax.spines['right'].set_color('None') #remove line on the right of figure
ax.legend(loc='upper right', fontsize=11, ncol=3, edgecolor='None')
ax.set_ylim(0, 32)
ax.set_xlabel('Time')
ax.set_ylabel('MW')
plt.title('Hourly Load Balance ({0}/{1}/{2}) '.
    format(peak_day_2035.loc[1,'year'],
    peak_day_2035.loc[1,'month'], peak_day_2035.loc[1, 'day']), color="Blue", fontsize=20)


#save the figure under the output folder
plt.savefig(path_to_outputs + "LB_" + output + ".pdf")
print("load balance graph is saved")


#########################################################
#Graph 4: Pie chart illustrating the energy mix in 2039
#########################################################


#load variable 'load_balance'
load_balance = pd.read_csv(path_to_outputs + "load_balance.csv")

#load variable "dispatch-wide.txt"
dispatch_wide = pd.read_csv(path_to_outputs + "dispatch-wide.csv")

#generate year, month, date, hour, minute, time and time 1 variables in each datafrme
for df in (load_balance, dispatch_wide):
    df['year'] = df['timestamp'].apply(str).str[0:4]
    df['year'] = pd.to_datetime(df.year, format = '%Y').dt.year
    df['month'] = df['timestamp'].apply(str).str[4:6]
    df['month'] = pd.to_datetime(df.month, format='%m').dt.month
    df['day'] = df['timestamp'].apply(str).str[6:8]
    df['day'] = pd.to_datetime(df.day, format='%d').dt.day
    df['hour'] = df['timestamp'].apply(str).str[9: 11]
    df['hour'] = pd.to_datetime(df.hour, format='%H').dt.hour
    df['minute'] = df['timestamp'].apply(str).str[11:13]
    df['minute'] = pd.to_datetime(df.minute, format = '%M').dt.minute
    df['time'] = pd.to_datetime(df[['year','month', 'day']])
    df['time1'] = pd.to_datetime(df[['year', 'month','day','hour','minute']])

#keep data only in 2039
load_balance_2039 = load_balance.loc[(load_balance['year'] == 2039)]
dispatch_wide_2039 = dispatch_wide.loc[(dispatch_wide['year']==2039)]


###############
#Add the value of green tariff credits
scenario = output[30:33]
if (scenario == "WO0"):
    load_balance_2039['WO_PV_Gen'] = 0
    print("No Green Tariff")
else:
    #Obtain capacity factor from west oahu
    CapFac_WO = pd.read_csv(path_to_CapFac + "west_oahu_cap_factor.csv")
    #hourly capacity factor information from 2006 to 2015

    #Compute the average of capacity factor of each hour or each date
    CapFac_WO = CapFac_WO.groupby(['month','day','hh'])[['cap_factor']].mean().reset_index()
    # Note that based on calculation, PV in West Oahu generation about 7 hours per day on average
    # This might be somewhat different from our pervious assumption that 5 hours per day generation on average

    CapFac_WO['WO_PV_Gen'] = (CapFac_WO['cap_factor']) * 10
    CapFac_WO['hour'] = CapFac_WO['hh']

    load_balance_2039 = pd.merge(load_balance_2039,
        CapFac_WO[['WO_PV_Gen', 'month', 'day', 'hour']],
        left_on=['month', 'day', 'hour'], right_on=['month', 'day', 'hour'],
        how='left')
    print("Green Tariff included")

################


#Subtract WO_PV_Gen from PurchasePowerZone
load_balance_2039['PurchasePowerZone'] = load_balance_2039['PurchasePowerZone'] -  load_balance_2039['WO_PV_Gen']
#convert 0 if the amount of purchased power is smaller than 0
load_balance_2039.loc[load_balance_2039.PurchasePowerZone < 0, 'PurchasePowerZone'] = 0


#set the value of variable at 0 if that variables are not included in the scenario.
list = ['Rooftop_PV-2020', 'Rooftop_PV-2020_PPA',
    'Rooftop_PV-2025', 'Rooftop_PV-2030', 'Rooftop_PV-2035',
    'Cogen_Power_Plant', 'Battery_Storage']
for var in list:
    if not var in dispatch_wide_2039.columns:
        dispatch_wide_2039.loc[:, var] = 0
        print('{} does not exist'.format(var))
    else:
        print('{} exists'.format(var))
dispatch_wide_2039 = dispatch_wide_2039.rename(columns={'Rooftop_PV-2020_PPA': 'PPAZone'})


load_balance_2039 = pd.merge(load_balance_2039,
    dispatch_wide_2039[['Battery_Storage', 'Cogen_Power_Plant',
    'Rooftop_PV-2025', 'Rooftop_PV-2030', 'Rooftop_PV-2035',
    'Rooftop_PV-0', 'Rooftop_PV-2020', 'PPAZone', 'time1']],
    left_on='time1', right_on='time1',
    how='left')


if 'TotalCoolingElectricityOffset' in load_balance_2039.columns:
    print("t")
else:
    load_balance_2039.loc[:,'TotalCoolingElectricityOffset'] = 0

load_balance_2039.tail(40)

#generate a variable presenting the sum of non-PPA PV generation
load_balance_2039['PV'] = (
    load_balance_2039['Rooftop_PV-0'] + load_balance_2039['Rooftop_PV-2020'] +
    load_balance_2039['Rooftop_PV-2025'] + load_balance_2039['Rooftop_PV-2030'] +
    load_balance_2039['Rooftop_PV-2035']
    )
load_balance_2039['Total_cogen']  = load_balance_2039['TotalCoolingElectricityOffset'] + load_balance_2039['Cogen_Power_Plant']


#keep only necessary variables
load_balance_2039 = load_balance_2039[['time1', 'zone_demand_mw', 'Total_cogen', 'PurchasePowerZone',
    'PPAZone', 'Battery_Storage', 'PV', 'WO_PV_Gen']]


#compute the daily total of each variable
load_balance_2039['total_mw'] = load_balance_2039['zone_demand_mw'].sum()
load_balance_2039['total_cogen'] = load_balance_2039['Total_cogen'].sum()
load_balance_2039['total_purchased_power'] = load_balance_2039['PurchasePowerZone'].sum()
load_balance_2039['total_PPA'] = load_balance_2039['PPAZone'].sum()
load_balance_2039['total_PV'] = load_balance_2039['PV'].sum()
load_balance_2039['total_battery'] = load_balance_2039['Battery_Storage'].sum()
load_balance_2039['total_green_tariff'] = load_balance_2039['WO_PV_Gen'].sum()


#compute the percentage of each generation sector to the total daily demand
list = ['cogen', 'purchased_power', 'PPA', 'PV', 'battery', 'green_tariff']
for var in list:
        load_balance_2039[var] = (load_balance_2039['total_'+ var] / load_balance_2039['total_mw'])*100
peak_day_2039_1 = load_balance_2039[['cogen', 'purchased_power', 'PPA','battery', 'PV', 'green_tariff' ]]
peak_day_2039_1 = peak_day_2039_1.rename(columns={'cogen': 'Cogeneration plant',
    'purchased_power': 'Purchased power',
    'battery' : 'Battery', 'PPA': 'PV with PPA', 'green_tariff':'Green Tariff'
    })

peak_day_2039_2 = peak_day_2039_1.T
peak_day_2039_2 = peak_day_2039_2.rename(columns={0: 'percent'})
peak_day_2039_2 = peak_day_2039_2.loc[:, ['percent']]

#Set the color of each pie
peak_day_2039_2['colors'] = ['pink', 'red', 'blue', 'orange', 'green', 'limegreen']
peak_day_2039_2['explode'] = 0

#Drop if the value of variable is zero
indexname = peak_day_2039_2[(peak_day_2039_2['percent'] == 0 )].index
peak_day_2039_2.drop(indexname, inplace=True)


#construct the pie chart
fig1, ax1 = plt.subplots()
wedges, texts, autotexts = ax1.pie (
    peak_day_2039_2['percent'],
    #reordered,
    #labels = ['Cogeneration Power Plant', 'Puchased Power','PPA PV', 'PV', 'Battery'],
    labels = peak_day_2039_2.index,
    #explode option arrows that one slide to be exploded out

    explode = peak_day_2039_2['explode'],
    # explode =(0,0,0,0,0,0),
    colors = peak_day_2039_2['colors'],
    #colors=['pink', 'red', 'blue', 'orange', 'green', 'purple'],

    #the percent listed as a fraction
    labeldistance = 1.05,
    autopct = '%1.1f%%',
    shadow = False,
    startangle = 90,
    textprops={'fontsize': 15}
)

#set up the size of fonts of label
plt.setp(texts, size=13)
#set up the size of fonts of value
plt.setp(autotexts, size=13)
plt.suptitle("Percentage of each generation sector in 2039", color='blue', fontsize=20)
#draw circle
centre_circle = plt.Circle((0,0),0.70,fc='white')
fig = plt.gcf()
fig.gca().add_artist(centre_circle)
#Equal aspect ratio
ax1.axis('equal')

#save the figure under the output folder
plt.savefig(path_to_outputs + "pie_" + output + ".pdf")
print("pie chart  is saved")


leg = ax.legend((line2, line3), ('Baseline: status-quo w/ futures prices',
    'Alternative scenario'), loc=(0.52, 0.11), edgecolor='None',
    facecolor='None', fontsize=12)
#Set the color of text in the legend as the same as the line
for line, text in zip(leg.get_lines(), leg.get_texts()):
    text.set_color(line.get_color())


########################################################
#Create a table
########################################################
#load variable 'load_balance'
cap_built = pd.read_csv(path_to_outputs + "gen_capacity_built_period.csv")


list = ['Rooftop_PV-2020', 'Rooftop_PV-2020_PPA',
    'Rooftop_PV-2025', 'Rooftop_PV-2030', 'Rooftop_PV-2035',
    'Cogen_Power_Plant', 'Battery_Storage']

for col in list:
    if col in cap_built.columns:
        print("{} exist".format(col))
    else:
        print("{} not exist".format(col))
        cap_built[col] = 0

cap_built['PV'] = (
    cap_built['Rooftop_PV-0'] + cap_built['Rooftop_PV-2020'] +
    cap_built['Rooftop_PV-2025'] + cap_built['Rooftop_PV-2030'] +
    cap_built['Rooftop_PV-2035']
    )



cap_built = cap_built[['period', 'Battery_Storage', 'PV',
    'Rooftop_PV-2020_PPA', 'Cogen_Power_Plant']]

cap_built = cap_built.rename(columns = {'period':'Period','Battery_Storage': 'Battery',
    'PV': 'on-campus PV', 'Rooftop_PV-2020_PPA':'on-campus PV with PPA', 'Cogen_Power_Plant': 'Cogen Plant'})

#set decimal points
cap_built = cap_built.round(2)

cap_built.to_csv(path_to_outputs + "cap_" + output + ".csv",
    header=['Period', 'Battery', 'PV', 'PV with PPA', 'Cogen plant'],
    index=False)
print("table is saved")


#remove input folder
input_path = os.path.join(cur_path + "/inputs_" + output + "/")
shutil.rmtree(input_path)

#remove output folder
#output_path = os.path.join(cur_path + output + "/")
#shutil.rmtree(output_path)
#print("sceniaor {}'s input folder is deleted".format(output))

#print ("The process is done")
