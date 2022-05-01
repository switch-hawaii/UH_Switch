"""
This script calculates the credits from the green tariff project in West Oahu
The script is based on the results in the folder "PPAC_projection"
The calculation of PPAC is based on the HECO's document in PPAC.

The structure of the output from this script is 'year' and 'TotalCredit'
The estimated total credits are the averaged monthly credit
The ouputs will be added to the results of Switch model.

output = "00L_EC1_NEC1_PV1_PPA1_CG0_WO3_VRM0"
VRM0 means virtual rider M option is not included in the model
VRM1 means that virtual rider M option is inlcuded in the model

Note: The difference between GreenTariff_WO_1.py and GreenTariff_WO_2 is that
the old version uses an assumption that PVs in west oahu generate electricity 5 hours per day while
GreenTariff_WO_2 uses a capacity factor from NREM
"""

import pandas as pd
import os
import os.path
import argparse

cur_path = os.getcwd() #obtain the current working directory


#set an option for preparing outputs
parser = argparse.ArgumentParser()
parser.add_argument('indir', type=str)
args = parser.parse_args()
output = args.indir

#for test (Need to revise these lines later)
#output = "EM0_00L_EC2_NEC1_PV1_PPA1_CG0_WO1_VRM1"

#set output and input directories
path_to_outputs = os.path.join(cur_path + "/" + output  + "/")
path_to_inputs = os.path.join(cur_path + "/inputs_" + output + "/")
path_to_CapFac = os.path.join(cur_path + "/processed_inputs/" )


###################################
# Set the size of Green tariff project and green tariff rate
###################################
#Set the size of PV capacity (MW)
PV_Cap = 10

#Set the capacity of Battery
Battery_MW = 5.5
Battery_MWh = Battery_MW * 4

#Set GTRate (dollars/MWh)
scenario = output[30:33]
if (scenario == "WO1"):
    GTRate = 100
    print("Green Tariff Rate if 10 cents/kWh")
elif (scenario == "WO2"):
    GTRate = 80
    print("Green Tariff Rate if 8 cents/kWh")
else:
    GTRate = 120
    print("Green Tariff Rate if 12 cents/kWh")
#Note that GTRate (green tariff rate) has a negative relation ship with the size of credits


###########################
# Calculate PPAC (dollar per MW)
###########################


#Create the empty dataframe
df = pd.DataFrame()

#Create year variable (year is from 2020 to 2039)
dict = {'year':range(2020,2040)}
df = pd.DataFrame(dict)

#Allocation percentage of demand-related purchased power adjustment (APD, %)
APD = [16.984] * 20
#Allocation percentage of energy-related purchased power adjustment (APE, %)
APE = [18.686] * 20
#Gross up to revenue requirement (farctor)
GRR = [1.097514] * 20
#Annual sales in DS Schedule
MWH = [1151300] * 20


#Construct Demand-related purchase adjustment [DPA]
Kal_Shortfall = [3289617] * 20
Kal_Cap = [32719000] * 20

AES_Cap = [65390116] * 20
AES_Avail_Bonus = [87004] * 20
AES_Reli_Bonus =[0] * 20

HPOWER_Cap = [11910221] * 20
HPOWER_Liq_Dam = [-24610] * 20

Gen_incent = [413760] * 20


#Construct Energy-related purchase adjustment [EPA]
Kal_Non_Fuel = [21271635] * 20
Kal_Var_OM = [0] * 20

AES_OM = [34432018] * 20

Solar_Farm = [2964940] * 20
Maint = [277375] * 20
Monitoring = [29758] * 20


#Create the table containing assigned variable and values
#add the name of column and their values
list= [APD, APE, GRR, MWH, Kal_Shortfall, Kal_Cap, AES_Cap, AES_Avail_Bonus, AES_Reli_Bonus,
    HPOWER_Cap, HPOWER_Liq_Dam, Gen_incent, Kal_Non_Fuel, Kal_Var_OM, AES_OM, Solar_Farm, Maint, Monitoring]

list1= ['APD', 'APE', 'GRR', 'MWH', 'Kal_Shortfall', 'Kal_Cap', 'AES_Cap', 'AES_Avail_Bonus', 'AES_Reli_Bonus',
    'HPOWER_Cap', 'HPOWER_Liq_Dam', 'Gen_incent', 'Kal_Non_Fuel', 'Kal_Var_OM', 'AES_OM', 'Solar_Farm', 'Maint', 'Monitoring']

for name, value in zip(list1, list):
    df[name]  = value

# Set the value of all variables related to AES zero after 2023.
# the contract between HECO and AES expires in 2022.
# HECO announed that this contract will not be extended.
AES_list = ['AES_Cap', 'AES_Avail_Bonus', 'AES_Reli_Bonus', 'AES_OM']
for list in AES_list:
    df.loc[df.year>=2023, [list]] = 0

#Calculate DPA, EPA and PPAC
#DPA (unit: thousand dollars)
df['DPA'] = ( df['Kal_Shortfall'] + df['Kal_Cap'] + df['AES_Cap'] +
        df['AES_Avail_Bonus'] + df['AES_Reli_Bonus'] + df['HPOWER_Cap'] + df['HPOWER_Liq_Dam'] + df['Gen_incent']
        )/1000


#EPA (unit: thousand dollars)
df['EPA'] =  (df['Kal_Non_Fuel'] + df['Kal_Var_OM'] + df['AES_OM'] + df['Solar_Farm']
    + df['Maint'] + df['Monitoring']
    )/1000

# Future utility-scale PV plans (size: MW)
pv_rate = 10 #cents/kWh
#Phase 1: three utility-scale PV projects are currently approved and under the constrcution
Hoohana = 52
Millilani = 39
Waiawa = 36

#Compute the purchaed power costs for Hoohana, Millilani and Waiawa solars
Solar_Farm_Costs_3 = (
    (Hoohana + Millilani  + Waiawa) * 1000 #conver from MW to KW
#        * 2200 #multiply the generation factor, assume that PV generate 5 hours per day
    * 1825 #multiply the generation factor, assume that PV generate 5 hours per day
    *0.135
    /1000 #convert the unit to the thousand dollars
    )
# the unit of Solar_Farm_Costs3 is thousand dollars
df.loc[df.year >=2021, 'EPA'] = df['EPA'] + Solar_Farm_Costs_3


#Phase 2: Oahu 594 MW
Solar_Farm_RFP = ((594 * 1000) #convert to MW to KW
#        * 2200 #multiply the generation factor, assume that PV generate 5 hours per day
    * 1825 #multiply the generation factor, assume that PV generate 5 hours per day
    * pv_rate/100
    /1000) #convert the unit to the unit to thousand dollars
# the unit of Solar_Farm_RFP is thousand dollars
df.loc[df.year >=2022, 'EPA'] = df['EPA'] + Solar_Farm_RFP


#Phase 3: Extra utility-scale PV projects which are not included in the current RFP
Extra_PV = 40
PV_p = (Extra_PV * 1000 #convert from MW to KW
#        * 2200 #multiply the generation factor, assume that PV generate 5 hours per day
    * 1825 #multiply the generation factor, assume that PV generate 5 hours per day
    * pv_rate/100
    /1000
    )
for year in range(2023, 2040,1):
    df.loc[df.year >= year, 'EPA'] = df['EPA'] + PV_p


#force that annual electricity sales falls by 1% in each year
for y in range(2020,2040):
    df.loc[df.year ==y, 'MWH'] = df['MWH']/((1 + 0.01)**(y-2020))
#1% reduction every year generates about 17% reduction at the end of time period
#2% reduction every year generates about 31% reduction at the end of time period

#########################
#calculate PPAC for each scenario
# (unit: cents/ kWh)
#########################

df['PPAC'] = (
    ((df['DPA'] * df['APD']/100) +
        (df['EPA'] * df['APE']/100)) * df['GRR'] * 100) / df['MWH']


#########################
# Merge energy charge and PPAC
# load estimaed energy charge data
#########################



EC = pd.read_csv(cur_path + "/../PPAC_projection/energy_charge_w_wo_utility_pv.csv" ,sep=",") #need to change the directory path
df = pd.merge(df,
     EC,
    left_on='year', right_on='year', how = 'left')
#calculate credits (= energy charge, dollar per MWh)


scenario = output[8:11]
scenario1 = output[0:3]
#Energy transition plan
if (scenario1 == 'EM0'):
    #renewable transition: PSIP + RFP 900 MW + 40MW in each year after 2023
    renewable_path='p'
else:
    #renewable transition: based on the results of the Oahu model
    renewable_path = 'opt'

#Oil price
if (scenario == 'EC1'):
    df['GT_credit'] = df['f_ec_brent_noPV_' + renewable_path] * 10 # Case: Future oil prices: med,
elif (scenario == 'EC2'):
    df['GT_credit'] =  df['f_ec_EIA_noPV_' + renewable_path] * 10
elif (scenario == 'EC3'):
    df['GT_credit'] =  df['f_ec_brent_lb_noPV_' + renewable_path] * 10


#Convert the unit of PPAC to `dollar per MWh'
df['PPAC'] = df['PPAC'] * 10


##########################################
# Compute annual electricity generation from West Oahu by using historical capacity factor
# from 2006 to 2015
##########################################
#Load capacity factor information from NREL
CapFac_WO = pd.read_csv(path_to_CapFac + "west_oahu_cap_factor.csv")
#hourly capacity factor information from 2006 to 2015

#Compute the average of capacity factor of each hour or each date
CapFac_WO = CapFac_WO.groupby(['month','day','hh'])[['cap_factor']].mean().reset_index()
# Note that based on calculation, PV in West Oahu generation about 7 hours per day on average
# This might be somewhat different from our pervious assumption that 5 hours per day generation on average

#Calaculte hourly electricity generation
CapFac_WO['PV_Gen'] = PV_Cap * CapFac_WO['cap_factor']

#Obtain the annual electricity consumption
CapFac_WO1 = CapFac_WO[['PV_Gen']].sum().reset_index()
PV_Gen = CapFac_WO1.loc[0,0].round(0)

#Add the computed annual electricity generation data to the original data
df['PV_Gen'] = PV_Gen

#########################################
# Compute total credits by using the range of green tariff rates
# and differernt PPAC calculation scneario and Utility-scale PV
#########################################

#Set contract year and operating year
initial_contract_year = 2023
initial_oper_year = 2025


#freeze the PPAC in the initial year and conver the unit of PPAC to dollars/MWh
ppac_ini = df.loc[df['year'] == initial_contract_year, 'PPAC'].values[0]
#obtain baseline credit that is a round-off number of the freezed ppac
df['BaselineCredit']=round(ppac_ini)

#calculate total credits
#cast: BaselineCredit > ppac
df.loc[df.BaselineCredit > ppac_ini, 'CreditRate'] = (
    df['GT_credit'] - GTRate)
df['TotalCredit'] = ((df['CreditRate'] * df['PV_Gen'])/12/1000)

# else: baslineCredit <= ppac
df.loc[df.BaselineCredit <= ppac_ini, 'CreditRate'] = (
    df['GT_credit'] + (
          ppac_ini - df['BaselineCredit']  #add extra credit
        ) - GTRate)
df['TotalCredit'] = ((df['CreditRate'] * df['PV_Gen'])/12/1000)



##################
#adding virtual rider M
##################

#output = "EM0_00L_EC1_NEC0_PV0_PPA0_CG0_WO0_VRM0"
scenario1 = output[12:16]
scenario = output[34:39]
print (output)
if (scenario1 == "NEC0" and scenario == "VRM0"):
    print("VRM option is not included")
    df['Demand_Charge'] = 0
elif (scenario1 == "NEC1" and scenario == "VRM0"):
    print("VRM option is not included")
    df['Demand_Charge'] = 0
elif (scenario1 == "NEC0" and scenario == "VRM1"):
    print("No grid defection and VRM option is included")
    df['Demand_Charge'] =[27, 28 ,30 ,31 ,33, 35, 37, 39, 41, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68, 71]
    df['Demand_Charge'] = df['Demand_Charge'] * 1000
else:
    print("30% grid defection and VRM option is included")
    df['Demand_Charge'] =[27, 29 ,30 ,32 ,34, 36, 38, 40, 42, 44, 47, 50, 53, 56, 59, 62, 66, 70, 74, 78]
    df['Demand_Charge'] = df['Demand_Charge'] * 1000
    #Set demand charge (dollars per MW)



#############################################
# Compute total credits with virtual rider M
#############################################

#Set the range of green tariff rate (unit: dollars per MWh)
df["TotalCredit"] = (
    # Credits from Demand Curtailment
    df["TotalCredit"] + ((Battery_MW * 0.75 * df['Demand_Charge'])/1000) #convert to thousand dollars
    )



#Delite Total Credits before operating years
df = df.loc[(df['year'] >= initial_oper_year)]
df = df.reset_index(drop=True)

df = df[['TotalCredit', 'PV_Gen']]
#df = df.loc[:, df.columns.str.startswith('TotalCredit')]

#add 'year' variable
df.insert(0, 'year', range(initial_oper_year, 2040))


#Convert the unit of the result from nominal to real
for y in range(2020,2040):
    df.loc[df.year ==y, 'TotalCredit'] = df['TotalCredit']/((1 + 0.02)**(y-2019))


#Save the results
df.to_csv(path_to_outputs + "GT_Credits.csv", index=False, header=True)
