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

#    m.PV_WO_GENS = Set(
#    initialize= ["West_Oahu_PV"]
#    )
    """
    m.gen_take_or_pay_cost = Param(m.GENERATION_PROJECTS, default=0.0)
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

    m.wo_ppa = Param(m.GENERATION_PROJECTS, within=Boolean)
    m.PV_WO_GENS = Set(initialize=m.GENERATION_PROJECTS, filter=lambda m, g: m.wo_ppa[g])

    m.PV_WO_GEN_TPS = Set(
        dimen =2,
        initialize= lambda m: (
            (g, tp)
                for g in m.PV_WO_GENS
                    for tp in m.TPS_FOR_GEN[g]
        )
    )

#    m.ppa_price_WO = Param(m.TIMEPOINTS)
    m.annual_credit = Param(m.TIMEPOINTS)
    m.PPAC = Param(m.TIMEPOINTS)
    m.ppa_price_wo = Param(m.PV_WO_GEN_TPS, within=NonNegativeReals)

#ser variable
    m.PV_WO_purchased = Var(m.PV_WO_GEN_TPS, within=NonNegativeReals)

#Set Constraint
    def rule(m, g, tp):
        return (
        m.PV_WO_purchased[g, tp] == m.gen_capacity_limit_mw[g] * (m.gen_max_capacity_factor[g, tp] if m.gen_is_variable[g] else 1.0)
        )
    m.Limit_PPAPuchased_WO = Constraint(
        m.PV_WO_GEN_TPS, rule=rule
    )


#inject electricity to demand zone
    def rule(m, z, tp):
        return sum(m.PV_WO_purchased[g, tp] for g in m.PV_WO_GENS)
    m.WO_PPAZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS,
        rule=rule)
    m.Zone_Power_Injections.append('WO_PPAZone')



#Calculate credits from West Oahu
# If the sign of total credit is plus, that means that the UH needs to pay to HECO (cost > benefit)
# If the sign of total credit is minus, the total amount of benefits is higher than costs (cost < benefit)

    def rule(m, tp):
        if m.annual_credit[tp] < m.PPAC[tp]:
            expr = sum(
                m.PV_WO_purchased[g, tp] * (
                    m.ppa_price_wo[g, tp]
                    - (m.PPAC[tp] - m.annual_credit[tp] )
                    - m.purchase_power_price[tp]

                )
                for g in m.PV_WO_GENS
            )

            return expr
        else:
            expr = sum(
                m.PV_WO_purchased[g, tp] * (
                    m.ppa_price_wo[g, tp] - m.purchase_power_price[tp]
                )
                for g in m.PV_WO_GENS
            )

            return expr
    m.TotalCredit = Expression(
        m.TIMEPOINTS, rule=rule,
    )
    m.Cost_Components_Per_TP.append('TotalCredit')


#load inputs
def load_inputs(m, switch_data, inputs_dir):
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'power_price_timepoint.csv'),
        # first column must show timepoint, and other column must be named 'purchase_power_price'
        autoselect=True,
        param=(m.purchase_power_price,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'ppa_price_wo_timepoint.csv'),
        autoselect=True,
        param=(m.ppa_price_wo,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'annual_credit_timepoint.csv'),
        autoselect=True,
        param=(m.annual_credit,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'PPAC_timepoint.csv'),
        autoselect=True,
        param=(m.PPAC,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'generation_projects_info.csv'),
        auto_select=True,
        param=(m.wo_ppa,)
    )
#    switch_data.load_aug(
#        filename=os.path.join(inputs_dir, 'generation_projects_info.csv'),
#        auto_select=True,
#        param=(m.gen_take_or_pay_cost)
#    )
