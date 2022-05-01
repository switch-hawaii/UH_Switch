"""
Compute the NPV of each scenario

NPV = value - cost

value = difference of electricity bill between the considered scnearios and the baseline scenario
baseline scearnio = the scenario without any investment in each oil price projection

cost = cost of the investment
"""


import pandas as pd
import os
import os.path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Rectangle
import numpy as np

import argparse
from os import rmdir
import shutil



cur_path = os.getcwd()
print(cur_path)


######
#set an option for preparing outputs
parser = argparse.ArgumentParser(description = 'Prepare net present value')
parser.add_argument('indir', type=str,
    help='Add the name of output folder. Ex) python compute_NPV.py EM0_10L_EC1_NEC0_PV0_PPA0_CG0'
    )

args = parser.parse_args()
print("Preparing outputs = {}".format(args.indir))
extra_inv_output = args.indir

#For test run
#extra_inv_output = "EM0_00L_EC3_NEC0_PV1_PPA1_CG0_WO1_VRM1"

scenario_EM = extra_inv_output[0:3]
scenario = extra_inv_output[8:16]
base_output = scenario_EM + "_00L_" + scenario + "_PV0_PPA0_CG0_WO0_VRM0"


path_to_base_output = os.path.join(cur_path + "/baseline/" + base_output + "/")
path_to_extra_inv_output = os.path.join(cur_path + "/" + extra_inv_output + "/")
#path_to_outputs = os.path.join(cur_path + "/" + output + "/")

#obtain total ebill
Base_totbill=pd.read_csv(path_to_base_output + 'summarycost.csv')
Extra_inv_totbill = pd.read_csv(path_to_extra_inv_output + 'summarycost.csv')

#calculate value of the investment
#equation: baseline(ec, non-ec, dc) - considered(ec, non-ec, dc, total,credits)
Base_totbill['Base_bill'] = Base_totbill['TotalEbill']
Base_totbill =  Base_totbill[['YearMonth', 'year', 'time', 'Base_bill']]

#Obtain total bill for basic investment and extra investment bill
#Basic_inv_totbill['Basic_inv_bill'] = Basic_inv_totbill['TotalEbill']
Extra_inv_totbill['Extra_inv_bill'] = Extra_inv_totbill['TotalEbill']


df = pd.merge(Base_totbill, Extra_inv_totbill[['YearMonth', 'Extra_inv_bill']], left_on = 'YearMonth',
right_on = 'YearMonth', how ='left')



#Difference between no investment and basic investment
df['Extra_inv_value'] = df['Base_bill'] - df['Extra_inv_bill']

#cost: amortizedcost, ppacost, fuelcost, cogenPPAcost
df = df.groupby('year')['Extra_inv_value'].sum().reset_index()
df['Extra_inv_value'] = df['Extra_inv_value']/1000000


#discount the bill and sum that up
#compute net present value of each year
df['NPV_Extra_inv_value_3'] = (df['Extra_inv_value'])/((1+0.01)**(df['year']- 2019))
df['NPV_Extra_inv_value_5'] = (df['Extra_inv_value'])/((1+0.02)**(df['year']- 2019))


#convert to the million dolar
#sum up the results of all years
test = df.loc[:,df.columns.str.startswith('NPV')].sum()
test = test.round(2)

df = pd.DataFrame(data=test)
df = df.loc[['NPV_Extra_inv_value_3', 'NPV_Extra_inv_value_5']]


df = df.reset_index()
df = df.rename(columns={'index': 'scenario', 0:'NPV'})

#create a bar graph
labels = ['Current scenario']
Dis3 = [df.at[0, 'NPV']]
Dis5 = [df.at[1, 'NPV']]

x = np.arange(len(labels)) #the lavel location
width = 0.1



plt.rcParams["figure.figsize"] = (9,6) #set the size of figure
fig, ax = plt.subplots()
rects1 = ax.bar(0, Dis3, 0.7, label='3% discount rate')
rects2 = ax.bar(2, Dis5, 0.7, label='5% discount rate')

# Add some text for labels, title and custom x-axis tick labels, etc.
ax.set_ylabel('Million 2019 dollars', fontsize=13)
ax.set_xticks(x+1) #
ax.set_xticklabels(labels, fontsize=13)
ax.set_ylim(-50,400)
ax.set_xlim(-1,3)
ax.legend(loc="best", frameon=False, fontsize=13)
ax.spines['top'].set_color('None') #remove line on the top of figure
ax.spines['right'].set_color('None') #remove line on the right of figure
ax.axhline(0, color='grey', lw=1)


def add_value_labels(ax, spacing=5):
    """Add labels to the end of each bar in a bar chart.

    Arguments:
        ax (matplotlib.axes.Axes): The matplotlib object containing the axes
            of the plot to annotate.
        spacing (int): The distance between the labels and the bars.
    """

    # For each bar: Place a label
    for rect in ax.patches:
        # Get X and Y placement of label from rect.
        y_value = rect.get_height()
        x_value = rect.get_x() + rect.get_width() / 2

        # Number of points between bar and label. Change to your liking.
        space = spacing
        # Vertical alignment for positive values
        va = 'bottom'

        # If value of bar is negative: Place label below bar
        if y_value < 0:
            # Invert space to place label below
            space *= -1
            # Vertically align label at top
            va = 'top'

        # Use Y value as label and format number with one decimal place
        label = "{:.1f}".format(y_value)

        # Create annotation
        ax.annotate(
            label,                      # Use `label` as label
            (x_value, y_value),         # Place label at end of the bar
            xytext=(0, space),          # Vertically shift label by `space`
            textcoords="offset points", # Interpret `xytext` as offset in points
            ha='center',                # Horizontally center label
            va=va)                      # Vertically align label differently for
                                        # positive and negative values.

# Call the function above. All the magic happens there.
add_value_labels(ax)


plt.savefig(path_to_extra_inv_output + "/NPV_" + extra_inv_output + ".pdf")

print("The figure presenting future bills is saved under the graphs folder")
