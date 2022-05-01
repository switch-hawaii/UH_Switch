"""
This code sets the case that UH decides to build cogeneration power plant with PPA

TODO list
 - 1) Need to add a feature that Cogen produces extra energy
"""

import os
from pyomo.environ import *

def define_components(m):
    #Add a cogen_ppa (ppa parice, dollar per MWh) column in GENERATION_PROJECTS input
    m.cogen_ppa = Param(m.GENERATION_PROJECTS, default=0.0)


    #Add total cost of cogen PPA to the bill
    m.CogenPPACostInTP = Expression(
        m.TIMEPOINTS,
        rule=lambda m, t: sum(
             m.cogen_ppa[g] * 1.182
             * m.GenCapacityInTP[g, t] * m.gen_availability[g]
             #* m.DispatchGen[g, t]
             for g in m.GENS_IN_PERIOD[m.tp_period[t]])

        )
    m.Cost_Components_Per_TP.append('CogenPPACostInTP')


#Cost for Extra Generations
#Need to fix to use this
#    m.CogenPPAExtraInTP = Expression(
#        m.TIMEPOINTS,
#        rule=lambda m, tp: sum(
#            m.cogen_ppa[g] for g in m.GENS_IN_PERIOD[m.tp_period[tp]] #set PPA0
#            * m.CogenCoolingOffset[g, tp] for g in m.COGEN_GENS
#        )
#    )
#    m.Cost_Components_Per_TP.append('CogenPPAExtraInTP')







#load inputs
def load_inputs(m, switch_data, inputs_dir):

    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'generation_projects_info.csv'),
        auto_select=True,
        param=(m.cogen_ppa)
    )
