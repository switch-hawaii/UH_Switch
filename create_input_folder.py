"""
This script generates an input folder by combining the input files in "processed_inputs" folder

To run this code, please type the following command on your Terminal window
"python create_input_folder.py name_of_scenario (ex. EM1_00L_EC1_NEC0_PV1_PPA1_CG0_WO1)""

EM: Energy Mix
EM0: PSIP + RFP 900 MW + 40 MW
EM1: The results of the Oahu model

Note that all of the input files are coming from "processed_inputs" folder.
If you want to change the value of some input files, it is better to change
the inputs file in 'processed_inputs' folder.
Then, create an input folder by using this script.

"""

import os
import pandas as pd
import argparse


#obtain current working directory
current_path = os.getcwd()

#set an option for preparing files in input folder
parser = argparse.ArgumentParser(description = 'Prepare inputs')
parser.add_argument('indir', type=str,
    help = "type the name of input folder"
    )
args = parser.parse_args()

new_folder = args.indir
input = new_folder


print("="*50)
print("Creating input folder")
print("Scenario = {}".format(args.indir))
print("="*50)

#delete # if you would like to test an individual scenario
#input = "EM0_00L_EC1_NEC0_PV0_PPA0_CG0_WO0_VRM0"
#new_folder="00L_EC1_NEC0_PV0_PPA0_CG0_WO0_VRM0"
#create a input folder
try:
    os.mkdir(current_path + "/inputs_" + new_folder)
except OSError:
    print("The input folder {} is replaced".format(new_folder))
else:
    print("The input folder {} is succefully created".format(new_folder))
new_folder = os.path.join(current_path + "/inputs_" + new_folder + "/")


#define the directory that store input files
input_folder = os.path.join(current_path + "/processed_inputs/")
#print(input_folder)

print(" ")
print(" ** Details of input scenario ** ")
print(" ")

#input = "EM0_00L_EC1_NEC0_PV0_PPA0_CG0_WO0_VRM0"
#set load profile
scenario = input[4:7]
if (scenario == "00L"):
    loads = pd.read_csv(input_folder + "loads.csv")
    print("No energy efficiency improvment")
elif (scenario == "10L"):
    loads = pd.read_csv(input_folder + "loads_red_10p.csv")
    print("10% energy efficiency imporvement")
elif (scenario == "20L"):
    loads = pd.read_csv(input_folder + "loads_red_20p.csv")
    print("20% energy efficiency improvement")
else:
    loads = pd.read_csv(input_folder + "loads_red_30p.csv")
    print("30% energy efficiency improvement")
loads.to_csv(new_folder + "loads.csv", index=False)

#set energy charge
scenario1 = input[0:3]
scenario = input[8:11]
if (scenario1 == "EM0" and scenario == "EC2"):
    ec = pd.read_csv(input_folder + "power_price_timepoint_high.csv")
    print("Future energy transition is based on PSIP + 900MW RFP and 40 MW each year")
    print("Energy charge is based on EIA forecast")

elif (scenario1 == "EM0" and scenario == "EC1"):
    print("Future energy transition is based on PSIP + 900MW RFP and 40 MW each year")
    print("Energy charge is based on futures price")
    ec = pd.read_csv(input_folder + "power_price_timepoint_mid.csv")

elif (scenario1 == "EM0" and scenario == "EC3"):
    print("Future energy transition is based on PSIP + 900MW RFP and 40 MW each year")
    ec = pd.read_csv(input_folder + "power_price_timepoint_low.csv")
    print("Energy charge is based on 1SD low futures price")

elif (scenario1 == "EM1" and scenario == "EC2"):
    print("Future energy transition is based on the results of the optimization model")
    ec = pd.read_csv(input_folder + "power_price_timepoint_high_opt.csv")
    print("Energy charge is based on EIA forecast")

elif (scenario1 == "EM1" and scenario == "EC1"):
    print("Future energy transition is based on the results of the optimization model")
    print("Energy charge is based on futures price")
    ec = pd.read_csv(input_folder + "power_price_timepoint_mid_opt.csv")

else:
    #scenario1 == "EM1" and scenario == "EC3"
    print("Future energy transition is based on the results of the optimization model")
    print("Energy charge is based on 1SD low futures price")
    ec = pd.read_csv(input_folder + "power_price_timepoint_low_opt.csv")


ec = ec.round({'purchase_power_price':4}) #limit the decimal points
ec.to_csv(new_folder + "power_price_timepoint.csv", index=False)


#set demand_charge and non-energy charge
scenario = input[12:16]
if (scenario == "NEC0"):
    print("No grid defection")
    demand_charge = pd.read_csv(input_folder + "demand_charge_period.csv")
    non_energy_charge = pd.read_csv(input_folder + "nonenergy_price_timepoint.csv")
else:
    print("30% grid defection")
    demand_charge = pd.read_csv(input_folder + "demand_charge_period_def30.csv")
    non_energy_charge = pd.read_csv(input_folder + "nonenergy_price_timepoint_def30.csv")

demand_charge.to_csv(new_folder + "demand_charge_period.csv", index=False)
non_energy_charge.to_csv(new_folder + "nonenergy_price_timepoint.csv", index=False)


#LOAD PROJECT_INFORMATION, BUILDING_COSTS,FUEL COSTS AND NON-FUEL ENERGY SOURCES
#project_info = pd.read_csv(input_folder + "generation_projects_info_1.csv")
project_info = pd.read_csv(input_folder + "generation_projects_info_planned.csv")
build_cost = pd.read_csv(input_folder + "gen_build_costs_planned_PV.csv")
non_fuel_energy_sources = pd.read_csv(input_folder + "non_fuel_energy_sources.csv")
fuel_cost = pd.read_csv(input_folder + "fuel_cost.csv")
capacity_factor = pd.read_csv(input_folder + "variable_capacity_factors_planned_PV.csv")


#Scenarios related to Cogen Power Plant
scenario = input[26:29]
if (scenario == "CG1"): #Cogen without PPA, no enforcement
    project_info = pd.read_csv(input_folder + "generation_projects_info_planned_cogen.csv")
    print("Project info is set with cogen")
elif (scenario == "CG2"): #Cogen without PPA, with enforcement
    cooling = pd.read_csv(input_folder + "cooling_demand.csv")
    cooling.to_csv(new_folder + "cooling_demand.csv", index=False)
    print("Cogen power plant and cooling demand are incuded")
elif (scenario == "CG3"): #Cogen with 11 cents/kWh  PPA, no enforcement
    project_info = pd.read_csv(input_folder + "generation_projects_info_cogen_PPA_11.csv")
    build_cost = pd.read_csv(input_folder + "gen_build_costs_cogen_PPA_planned_PV.csv")
    fuel_cost = pd.read_csv(input_folder + "fuel_cost_cogen_PPA.csv")
    non_fuel_energy_sources = pd.read_csv(input_folder + "non_fuel_energy_sources_cogen_PPA.csv")
    print("Cogen plant with 11 cents/kWh PPA is inlcuded ")
elif (scenario == "CG4"): #Cogen with 14 cents/kWh  PPA, no enforcement
    project_info = pd.read_csv(input_folder + "generation_projects_info_cogen_PPA_14.csv")
    build_cost = pd.read_csv(input_folder + "gen_build_costs_cogen_PPA_planned_PV.csv")
    fuel_cost = pd.read_csv(input_folder + "fuel_cost_cogen_PPA.csv")
    non_fuel_energy_sources = pd.read_csv(input_folder + "non_fuel_energy_sources_cogen_PPA.csv")
    print("Cogen plant with 14 cents/kWh PPA is inlcuded ")
elif (scenario == "CG5"): #Cogen with 17 cents/kWh PPA, no enforcement
    project_info = pd.read_csv(input_folder + "generation_projects_info_cogen_PPA_17.csv")
    build_cost = pd.read_csv(input_folder + "gen_build_costs_cogen_PPA_planned_PV.csv")
    fuel_cost = pd.read_csv(input_folder + "fuel_cost_cogen_PPA.csv")
    non_fuel_energy_sources = pd.read_csv(input_folder + "non_fuel_energy_sources_cogen_PPA.csv")
    print("Cogen plant with 17 cents/kwh PPA is inlcuded ")
elif (scenario == "CG6"): #Cogen with 14 cents PPA, with enforcement
    project_info = pd.read_csv(input_folder + "generation_projects_info_cogen_PPA_14.csv")
    build_cost = pd.read_csv(input_folder + "gen_build_costs_cogen_PPA_planned_PV.csv")
    cooling = pd.read_csv(input_folder + "cooling_demand.csv")
    cooling.to_csv(new_folder + "cooling_demand.csv", index=False)
    fuel_cost = pd.read_csv(input_folder + "fuel_cost_cogen_PPA.csv")
    non_fuel_energy_sources = pd.read_csv(input_folder + "non_fuel_energy_sources_cogen_PPA.csv")
    print("Cogen plant with PPA and cooling demand are inlcuded ")
else: #without cogen plant
    list = [project_info, build_cost]
    for df in list:
        indexname = df[(df['GENERATION_PROJECT'] == 'Cogen_Power_Plant')].index
        df.drop(indexname, inplace=True)
    non_fuel_energy_sources = pd.read_csv(input_folder + "non_fuel_energy_sources.csv")
    print("Cogen power plant is not included")

#PV project on campus
scenario = input[17:20]
if (scenario == "PV0"):
    list = [project_info, capacity_factor, build_cost]
    for df in list:
        list_var = ['Rooftop_PV-2025', 'Rooftop_PV-2030', 'Rooftop_PV-2035']
        for var in list_var:
            indexname = df[(df['GENERATION_PROJECT'] == var)].index
            df.drop(indexname, inplace=True)
else:
    print('PV project is included')

#PPA of PV
scenario = input[21:25]
if (scenario == "PPA0"):
    #get rid of the row for PPA
    list = [project_info, capacity_factor, build_cost]
    for df in list:
        indexname = df[(df['GENERATION_PROJECT'] == 'Rooftop_PV-2020_PPA')].index
        df.drop(indexname, inplace=True)
    print("No PPA PV porject")
else:
    print("With PPA PV project")

# PV project in West Oahu
scenario = input[30:33]
if (scenario == "WO0"):
    list = [project_info, capacity_factor]
    for df in list:
        indexname = df[(df['GENERATION_PROJECT'] == 'West_Oahu_PV')].index
        df.drop(indexname, inplace= True)
        print("No Greentariff project")
else:
    print("With Greentariff project")
    #Add input files related to WO project
#    files = ["PPAC_timepoint.csv", "annual_credit_timepoint.csv",
#        "ppa_price_wo_timepoint.csv"
#        ]
#    for var in files:
#        file = pd.read_csv(input_folder + var)
#        file.to_csv(new_folder + var, index=False)

#save inputs files into the input folder
capacity_factor.to_csv(new_folder + "variable_capacity_factors.csv", index=False)
project_info.to_csv(new_folder + "generation_projects_info.csv", index=False)
build_cost.to_csv(new_folder + "gen_build_costs.csv", index=False)
fuel_cost.to_csv(new_folder + "fuel_cost.csv", index=False)
non_fuel_energy_sources.to_csv(new_folder + "non_fuel_energy_sources.csv", index=False)


scenario = input[17:29]
if (scenario == "PV0_PPA0_CG0"):
    build_cost = pd.read_csv(new_folder + "/gen_build_costs.csv")
    build_cost.loc[1, "gen_storage_energy_overnight_cost"] = 52600000000
    build_cost.loc[2, "gen_storage_energy_overnight_cost"] = 52600000000
    build_cost.loc[3, "gen_storage_energy_overnight_cost"] = 52600000000
    build_cost.loc[4, "gen_storage_energy_overnight_cost"] = 52600000000
    build_cost.to_csv(new_folder + "gen_build_costs.csv", index=False)
    print("battery prices are adjusted")
else:
    print("not baseline scenario")


#add other input files
files = ["financials.csv" , "fuels.csv",
    "gen_build_predetermined.csv", "load_zones.csv",
    "periods.csv", "switch_inputs_version.txt", "timepoints.csv",
    "timeseries.csv", "gen_take_or_pay_cost.csv", "carbon_policies.csv"
    ]

for var in files:
    file = pd.read_csv(input_folder + var)
    file.to_csv(new_folder + var, index=False)


#############################
# MODULES
#construct modules.txt which contains the list of modules used to run the model
#############################
module = open(new_folder + "modules.txt","w")
print("module.txt is created")

core0 = ("# Core Modules")
core1 = ("switch_model")
core2 = ("switch_model.timescales")
core3 = ("switch_model.financials")
core4 = ("switch_model.balancing.load_zones")
core5 = ("switch_model.energy_sources.properties")
core6 = ("switch_model.generators.core.build")
core7 = ("switch_model.generators.core.dispatch")
core8 = ("switch_model.reporting")

module.write("{}" "\n" "{}" "\n" "{}" "\n" "{}" "\n"  \
    "{}" "\n" "{}" "\n" "{}" "\n" "{}" "\n" "{}".
    format(core0, core1, core2, core3, core4, core5, core6, core7, core8))

custom0 = ("# Custom Modules")
custom1 = ("switch_model.generators.core.no_commit")
custom2 = ("switch_model.energy_sources.fuel_costs.simple")
custom3 = ("switch_model.generators.extensions.storage")
custom4 = ("switch_model.policies.carbon_policies")

module.write("\n" "\n" "{}" "\n" "{}" "\n" "{}" "\n" "{}" "\n" "{}".
    format(custom0, custom1, custom2, custom3, custom4))

UH0 = ("#UH Modules")
#set condition for UH Modules
#considered factors: PPA, CG
scenario = input[21:25]
if (scenario == "PPA0"):
    UH1 = ("#scenario: no PPA PV")
    UH2 = ("UH_module.demand_charge")
    UH3 = (" ")
else:
    UH1 = ("#scenario: PPA PV ")
    UH2 = ("UH_module.demand_charge")
    UH3 = ("UH_module.PPA_PV_Varcost")
module.write("\n" "\n" "{}" "\n" "{}" "\n" "{}" "\n" "{}".
    format(UH0, UH1, UH2, UH3))

scenario = input[26:29]
Cogen0 = ("#Cogen plant modules")
if (scenario == "CG1"):
    Cogen1 = ("#Scenario: Cogen plant without enforcement")
    Cogen2 = ("UH_module.cogen_only_no_enforce")
    Cogen3 = (" ")
elif (scenario == "CG2"):
    Cogen1 = ("#Scenario: Cogen plant with enforcement that cogen follows cooling demand")
    Cogen2 = ("UH_module.cogen_only_w_enforce")
    Cogen3 = ("")
elif (scenario == "CG3"):
    Cogen1 = ("#Scenario: Cogen plant (PPA) without enforcement that cogen follows cooling demand")
    Cogen2 = ("UH_module.cogen_only_no_enforce")
    Cogen3 = ("UH_module.PPA_cogen")
elif (scenario == "CG4"):
    Cogen1 = ("#Scenario: Cogen plant (PPA) without enforcement that cogen follows cooling demand")
    Cogen2 = ("UH_module.cogen_only_no_enforce")
    Cogen3 = ("UH_module.PPA_cogen")
elif (scenario == "CG5"):
    Cogen1 = ("#Scenario: Cogen plant (PPA) without enforcement that cogen follows cooling demand")
    Cogen2 = ("UH_module.cogen_only_no_enforce")
    Cogen3 = ("UH_module.PPA_cogen")
elif (scenario == "CG6"):
    Cogen1 = ("#Scenario: Cogen plant (PPA) with enforcement that cogen follows cooling demand")
    Cogen2 = ("UH_module.cogen_only_w_enforce")
    Cogen3 = ("UH_module.PPA_cogen")
else:
    Cogen1 = ("#Scenario: Cogen plant is not encluded")
    Cogen2 = ("")
    Cogen3 = ("")
module.write("\n" "\n" "{}" "\n" "{}" "\n" "{}" "\n" "{}".
    format(Cogen0, Cogen1, Cogen2, Cogen3))


# PV project in West Oahu
#scenario = input[26:29]
#West_Oahu0 = ("#Greentariff project")
#if (scenario == "WO1"):
#    West_Oahu1 = ("#Greentariff project is inlcuded")
#    West_Oahu2 = ("UH_module.PV_West_Oahu_1")
    #West_Oahu2 = ("UH_module.PV_West_Oahu")
    #"UH_module.PV_West_Oahu" does not let Switch chooses the optimal size of
    # WO project. I needs to be updated. PV_West_Oahu_1 tries to ptimize the project
    # based on earch time point
#else:
#    West_Oahu1 = ("#Greentariff project is NOT included")
#    West_Oahu2 = (" ")
#module.write("\n" "\n" "{}" "\n" "{}" "\n" "{}".
#    format(West_Oahu0, West_Oahu1, West_Oahu2))


module.close()

print(" ")
print("input folder inputs_{} is succefully created".format(input))
print("="*50)
