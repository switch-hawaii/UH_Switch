"""
This module add cogeneration power plant to the system
The congeneration power plant comes with a feature of extra electricity generation
by using wasted heat
The extra electricity generation is set as 18.2% percent of total electricity generated from cogeneration plant.
The extra generation is NOT linked to any specific demand profile.
"""

import os
from pyomo.environ import *


def define_components(m):
    #Set the generated electricity from "Cogen_power_plant" in each time point
    m.COGEN_GENS = Set(
        initialize=["Cogen_Power_Plant"]

        #initialize=["Cogen_Power_Plant"],
        #filter=lambda m, g: g in m.GENERATION_PROJECTS
        #TODO: check whether this below line is needed
        #Test whether the model works properly without this line
        #filter: A boolean function used during construction to indicate if
        # a potential new member should be assigned to the set

    )

    m.COGEN_GEN_TPS = Set(
        dimen =2,
        initialize=lambda m: (
            (g, tp)
                for g in m.COGEN_GENS
                    for tp in m.TPS_FOR_GEN[g]))


    #Set the parameter that decribes the fraction of electricity generated from the Chiller is 18.2%
    m.cogen_electricity_offset_fraction = Param(
        m.COGEN_GENS,
        initialize={'Cogen_Power_Plant': 0.182}
    )
    #Set the maximum possible electricity offset
    m.cogen_max_electricity_offset = Param(
        m.COGEN_GEN_TPS,
        #Question: Why infinity?
        default=float('infinity')
    )


    m.CogenCoolingOffset = Var(m.COGEN_GEN_TPS, within=NonNegativeReals)


    m.Max_Cogen_Offset_Production = Expression(
        m.COGEN_GEN_TPS,
        rule = lambda m, g, tp:
            m.cogen_electricity_offset_fraction[g] * m.DispatchGen[g, tp]
    )

    #Contraint: the amount of electricity that generated from the chiller should be smaller than
    # the amount from the cogen

    #No Excess Cooling. This constraint allows to deliver electricirty only the
    #amount that chiller used
    def rule(m, g, tp):
        if m.cogen_max_electricity_offset == float('infinity'):
            return Constraint.Skip
        else:
            return (
            m.CogenCoolingOffset[g, tp] <= m.Max_Cogen_Offset_Production[g, tp]
            )
    m.No_Excess_Cooling = Constraint(
        m.COGEN_GEN_TPS,
        rule=rule
    )


    # Electricity from chiller
    def rule(m, z, tp):
        return sum(
            m.CogenCoolingOffset[g, tp]
            for g in m.COGEN_GENS
            if m.gen_load_zone[g] == z and (g, tp) in m.GEN_TPS
        )
    m.TotalCoolingElectricityOffset = Expression(
        m.LOAD_ZONES, m.TIMEPOINTS,
        rule=rule
    )
    m.Zone_Power_Injections.append('TotalCoolingElectricityOffset')
#    m.Cost_Components_Per_TP.append('TotalCoolingElectricityOffset')

    # The cost of Electricity from chiller
#    m.CogenCoolingOffsetCost = Expression(
#        m.TIMEPOINTS, rule=lambda m, tp: m.CogenCoolingOffset[g, tp]
#        for g in m.COGEN_GENS
#    )

#    m.Cost_Components_Per_TP.append('CogenCoolingOffsetCost')



    # variables for amount of power bought (supplied from outside) and sold (delivered to outside)
#    m.PurchasePower = Var(m.TIMEPOINTS, within=NonNegativeReals)

#    m.PurchasePowerZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS, rule=lambda m, z, tp: m.PurchasePower[tp])
    # add PurchasePower to list of sources available to satisfy demand (along with any on-site generation)
#    m.Zone_Power_Injections.append('PurchasePowerZone')
    # Above lines let calculate the amount of PurchasePower in each timepoint

    # cost and revenue from power purchases and sales during each timepoint
#    m.PurchasedPowerCost = Expression(
#        m.TIMEPOINTS, rule=lambda m, tp: m.PurchasePower[tp] * m.purchase_power_price[tp]
#    )
#    m.Cost_Components_Per_TP.append('PurchasedPowerCost')
