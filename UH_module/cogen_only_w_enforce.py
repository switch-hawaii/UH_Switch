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
    # colling demand of Chiller
    m.cooling_demand = Param(m.TIMEPOINTS)

    #Set the generated electricity from "Cogen_power_plant" in each time point
    m.COGEN_GENS = Set(
        initialize=["Cogen_Power_Plant"]

    )
    #Set electricity generation from cogeneration plant at each timepoint
    m.COGEN_GEN_TPS = Set(
        dimen =2,
        initialize=lambda m: (
            (g, tp)
                for g in m.COGEN_GENS
                    for tp in m.TPS_FOR_GEN[g]))


    #set the parameter that decribes the fraction of electricity generated from the Chiller is 18.2%
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

#define that extra generation is certain percentage of total electricity generated from the plant
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
            m.CogenCoolingOffset[g, tp] == m.Max_Cogen_Offset_Production[g, tp]
            )
    m.No_Excess_Cooling = Constraint(
        m.COGEN_GEN_TPS,
        rule=rule
    )

 #set constrain that the amount of cooling demand offset by cogen is the same as the cooling demand in each time point
    def rule(m, g, tp):
        return(
        #m.CogenCoolingOffset: the amount of electricity that can generated from hybrid chiller
        # 0.182 * total dispatced electricity
        m.CogenCoolingOffset[g, tp] == m.cooling_demand[tp]
        )
    m.Cooling_Demand = Constraint(
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



def load_inputs(m, switch_data, inputs_dir):
    switch_data.load_aug(
        filename = os.path.join(inputs_dir, 'cooling_demand.csv'),
        auto_select=True,
        param=(m.cooling_demand)
    )
