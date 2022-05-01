""""
This is the custom module that describes Greentariff PV project in West Oahu
The module calculates the amount of credits and costs having PV in West Oahu land
The calculation is follow the equation presented below.

    PV project 10MW
    Greentariff builling method is applied
    Two different cases should be considered
    1) annual credit < PPAC
    Ebill = [(elec_heco * ECRF) + (PV_PPA1 * PPA) + Fixed charge]
    - [(PV_WO * ECRF) + (PV_WO * (PPAC - Annual credit)) - (PV_WO * PPA_WO)]

    2) Annual credit >= PPAC
    Ebill = [(elec_heco * ECRF) + (PV_PPA1 * PPA) + Fixed charge]
    - [(PV_WO * ECRF)) - (PV_WO * PPA_WO)]

"""

import os
from pyomo.environ import *

def define_components(m):

#set variables
# In this description, I would like to make the Switch decides how much PV built in each investment period


#set ppa_price_WO
    m.ppa_price_wo = Param(m.GENERATION_PROJECTS, m.PERIODS, default = 0.0 )
#    m.ppa_price_wo = Param(m.GENERATION_PROJECTS, m.TIMEPOINTS, default=0.0)
#These two variables vary in each month or year. These have not been set yet.
    m.annual_credit = Param(m.TIMEPOINT)
    m.PPAC = Param(m.GENERATION_PROJECTS, m.PERIODS, default = 0.0)
    m.ECRF_period = Param(m.GENERATION_PROJECTS, m.PERIODS, default = 0.0)
#    m.PPAC = Param(m.TIMEPOINTS)


#Calculate credits from West Oahu
# If the sign of total credit is plus, that means that the UH needs to pay to HECO (cost > benefit)
# If the sign of total credit is minus, the total amount of benefits is higher than costs (cost < benefit)

    def rule(m, t):
        expr = sum(
                (m.GenCapacityInTP[g, t] * m.gen_availability[g]
                * (m.gen_max_capacity_factor[g, t] if g in m.VARIABLE_GENS else 1.0))
                    * (m.ppa_price_wo[g, m.tp_period[t]] - m.ECRF_period[g, m.tp_period[t]] )
                    #* (m.ppa_price_wo[g, m.tp_period[t]] - m.PPAC[m.tp_period[t]])
                for g in m.GENS_IN_PERIOD[m.tp_period[t]]
            )

        return expr
    m.TotalCredit = Expression(m.TIMEPOINTS, rule=rule)
    m.Cost_Components_Per_TP.append('TotalCredit')


"""
    def rule(m, t):
        if m.annual_credit[t] < m.PPAC[t]:
            expr = sum(
                (m.GenCapacityInTP[g, t] * m.gen_availability[g]
                * (m.gen_max_capacity_factor[g, t] if g in m.VARIABLE_GENS else 1.0))
                    * (
                    m.ppa_price_wo[g, m.tp_period[t]]
                    - (m.PPAC[t] - m.annual_credit[t])
                    - m.purchase_power_price[t]
                )
                for g in m.GENS_IN_PERIOD[m.tp_period[t]]
            )

            return expr
        else:
            expr = sum(
                (m.GenCapacityInTP[g, t] * m.gen_availability[g]
                * (m.gen_max_capacity_factor[g, t] if g in m.VARIABLE_GENS else 1.0))
                    * (
                    m.ppa_price_wo[g, m.tp_period[t]] - m.purchase_power_price[t]
                )
                for g in m.GENS_IN_PERIOD[m.tp_period[t]]
            )

            return expr
    m.TotalCredit = Expression(
        m.TIMEPOINTS, rule=rule,
    )
    m.Cost_Components_Per_TP.append('TotalCredit')
"""

#load inputs
def load_inputs(m, switch_data, inputs_dir):
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'annual_credit_timepoint.csv'),
        autoselect=True,
        param=(m.annual_credit,)
    )
#    switch_data.load_aug(
#        filename=os.path.join(inputs_dir, 'PPAC_timepoint.csv'),
#        autoselect=True,
#        param=(m.PPAC,)
#    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'PPAC_period.csv'),
        autoselect=True,
        param=(m.PPAC,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'power_price_period.csv'),
        autoselect=True,
        param=(m.ECRF_period,)
    )

#    switch_data.load_aug(
#        filename=os.path.join(inputs_dir, 'ppa_price_wo_timepoint.csv'),
#        auto_select=True,
#        param=(m.ppa_price_wo,)
#    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'ppa_price_wo_period.csv'),
        auto_select=True,
        param=(m.ppa_price_wo,)
    )


    """
    #This code is from Matthias. The gen_take_or_pay_cost changes in each period
    #In this version, gen_take_or_pay_cost varies in different period

    m.gen_take_or_pay_cost = Param(m.GENERATION_PROJECTS, m.PERIODS, default=0.0)
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



    m.gen_take_or_pay_cost = Param(m.GENERATION_PROJECTS, default=0.0)
    #In this version, gen_take_or_pay_cost does not change

    m.GenTakeOrPayCostsInTP = Expression(
        m.TIMEPOINTS,
        rule=lambda m, t: sum(
             m.gen_take_or_pay_cost[g]
             * (
                m.GenCapacityInTP[g, t] * m.gen_availability[g]
                * (m.gen_max_capacity_factor[g, t] if g in m.VARIABLE_GENS else 1.0)
             )
            for g in m.GENS_IN_PERIOD[m.tp_period[t]]
        )
    )
    m.Cost_Components_Per_TP.append('GenTakeOrPayCostsInTP')
    """
