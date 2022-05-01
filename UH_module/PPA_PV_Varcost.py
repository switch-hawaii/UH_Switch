"""
This code add PPA PV project in the model.
Compare to the model 'PPA_PV_no_cogen.py', this module allows Switch to set the capacity of PPA project.
The project with PPA does not require an installation cost but needs to pay PPA.
In this code, PPA is indicated as gen_take_or_pay_cost.
17 cent/kWh is 170 in gen_take_or_pay_cost (dollar/mWh).


"""

import os
from pyomo.environ import *

def define_components(m):

#set variables
    """
    #This code is a revision of Matthias'code that allow gen_take_or_pay_cost varies in each timepoints
    m.gen_take_or_pay_cost = Param(m.GENERATION_PROJECTS, m.TIMEPOINTS, default=0.0)
    m.GenTakeOrPayCostsInTP = Expression(
        m.TIMEPOINTS,
        rule=lambda m, t: sum(
             m.gen_take_or_pay_cost[g, m.tp_period[t]]
             * (
                m.GenCapacityInTP[g, t] * m.gen_availability[g]
                * (m.gen_max_capacity_factor[g, t] if g in m.VARIABLE_GENS else 1.0)
             )
            for g in m.GENS_IN_PERIOD[m.tp_period[t]]
        )
    )
    m.Cost_Components_Per_TP.append('GenTakeOrPayCostsInTP')
    """


    #This code is from Matthias. The gen_take_or_pay_cost changes in each period

    #set PPA (=gen_take_or_pay_cost)
    m.gen_take_or_pay_cost = Param(m.GENERATION_PROJECTS, m.PERIODS, default=0.0)

    #Expression for total gen_take_or_pay_cost per month and add it to total costs
    m.GenTakeOrPayCostsInTP = Expression(
        m.TIMEPOINTS,
        rule=lambda m, t: sum(
             m.gen_take_or_pay_cost[g, m.tp_period[t]]
             * (
                m.GenCapacityInTP[g, t] * m.gen_availability[g]
                * (m.gen_max_capacity_factor[g, t] if g in m.VARIABLE_GENS else 1.0)
             )
            for g in m.GENS_IN_PERIOD[m.tp_period[t]]
        )
    )
    m.Cost_Components_Per_TP.append('GenTakeOrPayCostsInTP')


#load inputs
def load_inputs(m, switch_data, inputs_dir):

    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'gen_take_or_pay_cost.csv'),
        auto_select=True,
        param=(m.gen_take_or_pay_cost)
    )
