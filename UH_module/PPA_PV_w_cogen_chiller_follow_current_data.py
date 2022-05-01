"""
With cogen and the chiller under cogen fulfill cooling demand


TODO:
    1. Need to set the amount of offset by cogen is the same as the amount of coolind demand dataset
        - Understand the structure of the code
        - Try to find out the way to connect the code and dataset
        - The dataset for cooling demand is 15 min basis
        - The dataset that switch uses is hour basis
"""


import os
from pyomo.environ import *

def define_components(m):
    m.ts_month = Param(m.TIMESERIES)
    m.MONTHS = Set(initialize=lambda m:
        sorted(set(m.ts_month[ts] for ts in m.TIMESERIES))
    )

    #check whether the project is PPA (1) or not (0)
    m.gen_is_ppa = Param(m.GENERATION_PROJECTS, within=Boolean)

    #Set power generated under PPA in each timepoint by seperating into PPA project
    m.PPA_GENS = Set(initialize=m.GENERATION_PROJECTS, filter=lambda m, g: m.gen_is_ppa[g])
    m.PPA_GEN_TPS = Set(
        dimen=2,
        initialize=lambda m: (
            (g, tp)
                for g in m.PPA_GENS
                    for tp in m.TPS_FOR_GEN[g]))
    """
    TPS.FOR_GEN[g] is set in the module dispatch.py under generator/core folder
    TPS_FOR_GEN[g] is a set array showing all timepoints when a
    project is active. These are the timepoints corresponding to
    PERIODS_FOR_GEN. This is the same data as GEN_TPS,
    but split into separate sets for each project.
    """

    #PPA price
    m.ppa_price = Param(m.PPA_GEN_TPS, within=NonNegativeReals)
    # price of buying or selling power (per MWh) during each timepoint (from 'power_price_timepoint.tab')
    m.purchase_power_price = Param(m.TIMEPOINTS)

    #marginal price
    m.marginal_power_price = Param(m.TIMEPOINTS)
    #nonenergy price
    m.nonenergy_price = Param(m.TIMEPOINTS)
    # demand charges per peak MW during each period (from 'power_price_period.tab')
    m.demand_charge = Param(m.PERIODS, default=0.0)

    # colling demand of Chiller
    m.cooling_demand = Param(m.TIMEPOINTS)

    #Set the generated electricity from "Cogen_power_plant" in each time point
    m.COGEN_GENS = Set(
        initialize=["Cogen_Power_Plant"]
    )

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


    # variables for amount of power bought (supplied from outside) and sold (delivered to outside)
    m.PurchasePower = Var(m.TIMEPOINTS, within=NonNegativeReals)
    m.PPAPurchased = Var(m.PPA_GEN_TPS, within=NonNegativeReals)
    #m.CogenPower = Var(m.COGEN_GEN_TPS, within=NonNegativeReals)
    #amount of electricity offset that produced from each cogen in each time point
    m.CogenCoolingOffset = Var(m.COGEN_GEN_TPS, within=NonNegativeReals)


    #########################################################################################
    # Set Constrains for the amount of purchased power from HECO and PPA and power generated from cogen
    #########################################################################################

    # must accept all output from PPA projects (and no more)
    # NOTE: these projects should be omitted from gen_build_costs.tab unless you
    # to prevent building more copies of the project in addition to the PPA
    m.Limit_PPAPurchased = Constraint(
        m.PPA_GEN_TPS,
        rule=lambda m, g, tp:
            m.PPAPurchased[g, tp]
            ==
            m.gen_capacity_limit_mw[g]
            * (m.gen_max_capacity_factor[g, tp] if m.gen_is_variable[g] else 1.0) #original code
			# I think that it should be m.gen_is_ppa[g] instead of gen_is_variable in order to consider
			# only the project under ppa

    )

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

##############################################################################
# Calculate Peak Demand
##############################################################################

    # peak power variables
    m.MonthlyPeakPurchasedPower = Var(m.PERIODS, m.MONTHS, within=NonNegativeReals)
    m.AnnualPeakPurchasedPower = Var(m.PERIODS, within=NonNegativeReals)
    # force these to take the right values
    m.Calculate_MonthlyPeakPurchasedPower = Constraint(m.TIMEPOINTS, rule=lambda m, tp:
        (m.MonthlyPeakPurchasedPower[m.tp_period[tp], m.ts_month[m.tp_ts[tp]]])
        >=
        (m.PurchasePower[tp]+ sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS))
    )
    m.Calculate_AnnualPeakPurchasedPower = Constraint(m.PERIODS, m.MONTHS, rule=lambda m, p, mo:
        m.AnnualPeakPurchasedPower[p]
        >=
        m.MonthlyPeakPurchasedPower[p, mo]
    )

    ########################################################################################################################
    # Add purchases and sales to model's load balance
    ########################################################################################################################
    # Power purchased from HECO
    m.PurchasePowerZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS, rule=lambda m, z, tp: m.PurchasePower[tp])
    # add PurchasePower to list of sources available to satisfy demand (along with any on-site generation)
    m.Zone_Power_Injections.append('PurchasePowerZone')
    # add SellPower to list of loads (along with on-site loads)

    # Power purhcased under PPA agreeement (PV on campus)
    m.PPAZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS, rule=lambda m, z, tp:
        sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS))
    m.Zone_Power_Injections.append('PPAZone')

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

    #################################################
    # Calculate the cost for the UH
    ##################################################

    #Calculate the cost of natural gas for each timepoint
    #m.NaturalGasCost= Expression(
    #    m.TIMEPOINTS, rule=lambda m, tp:
    #    sum(m.natural_gas_price[g, tp] * m.CogenPower[g, tp]* 1.25 for g in m.COGEN_GENS))
#        sum(m.natural_gas_price[g, tp] * m.CogenPower[g, tp] for g in m.Cogen_GENS))
    #m.Cost_Components_Per_TP.append('NaturalGasCost')
    #Question: how can I obtain the total consumption of natural gas (NaturalGasConsumption[tp])
    # Todo:  Need to change CogenPower to natural gas consumption
    # 1.25 indicates the output/input ratio which illustrates the relationship between the amount of
    # natural gas added into the system and the amount of electricity generated
    # 1.25 is not the number that I checked with cogen developer yet. So the number will be changed in the future


    # cost and revenue from power purchases and sales during each timepoint
    m.PurchasedPowerCost = Expression(
        m.TIMEPOINTS, rule=lambda m, tp: m.PurchasePower[tp] * m.purchase_power_price[tp]
    )
    m.Cost_Components_Per_TP.append('PurchasedPowerCost')


    m.PPACost = Expression(
        m.TIMEPOINTS,
        rule=lambda m, tp:
        sum(m.PPAPurchased[g, tp] * m.ppa_price[g, tp] for g in m.PPA_GENS))
    m.Cost_Components_Per_TP.append('PPACost')

    #marginal value of PPA
    #m.ValueofPPA = Expression(
    #    m.TIMEPOINTS,
    #    rule=lambda m, tp: sum(m.PPAPurchased[g, tp] * m.marginal_power_price[tp] for g in m.PPA_GENS)
    #    )
    #m.Cost_Components_Per_TP.append('ValueofPPA')

    # m.PPACostNeg = Expression(
    #     m.TIMEPOINTS,
    #     rule=lambda m, tp: -1* m.PPACost[tp])
    # m.Cost_Components_Per_TP.append('PPACostNeg')

    # m.CapacityCost = Expression(
    #     m.TIMEPOINTS,
    #     rule=lambda m, tp:
    #         sum(
    #             m.GenCapacity[g, m.tp_period[tp]]
    #             * m.gen_max_capacity_factor[g, tp]
    #             * m.ppa_price[g, tp]
    #             for g in m.PPA_GENS
    #         )
    # )
    # m.Cost_Components_Per_TP.append('CapacityCost')

    m.NonEnergyCharge = Expression(
        m.TIMEPOINTS, rule=lambda m, tp:
        (sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS) + m.PurchasePower[tp]) * m.nonenergy_price[tp])
    m.Cost_Components_Per_TP.append('NonEnergyCharge')

    # demand charges during each period (annual cost)

    def calc(m, p):
        annual_total_charge = m.demand_charge[p] * sum(
             (m.MonthlyPeakPurchasedPower[p, mo] + m.AnnualPeakPurchasedPower[p]) / 2
                 for mo in m.MONTHS
        ) * 12/len(m.MONTHS) # convert monthly average to annual (m.MONTHS may not have 12 entries)
        return annual_total_charge
    m.DemandCharges = Expression(m.PERIODS, rule=calc)
    m.Cost_Components_Per_Period.append('DemandCharges')

"""
# Alternative code to estimate demand charge
    m.DemandCharges = Expression(m.PERIODS, rule = lambda m, p :
        m.demand_charge[p] * sum((m.MonthlyPeakPurchasedPower[p, mo] + m.AnnualPeakPurchasePower[p])/2 for mo in m.MONTHS
        )*12/len(m.MONTHS)
    m.Cost_Components_per_TP.append('DemandCharges')

"""


    # if wanted, you can declare a monthly base charge for each period (stored in power_price_period.tab),
    # then read that into a parameter, create an Expression that scales it up to an annual cost,
    # and append that expression to the m.Cost_Components_Per_Period list (each component in that
    # list is actually an annual cost).

    # m.Bound_System_Cost = Constraint(rule=lambda m: m.SystemCost >= -1e20)

    # total sales to HECO during each period must not exceed total purchases (net zero, but not net-negative)
    #m.Net_Non_Negative = Constraint(m.PERIODS, rule=lambda m, p:
    #    sum(m.SellPower[tp] * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p]) <=
    #    sum(sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS) * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p])
    #)

    #m.ConstraintPPAPurchased= Constraint(m.PERIODS, rule=lambda m, p:
    #    sum(sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS) * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p])
    #    <=
    #    (sum(m.DispatchGen[g, tp] * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p] for g in m.PPA_GENS ))
    #)



def load_inputs(m, switch_data, inputs_dir):
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'timeseries.tab'),
        select=('TIMESERIES', 'ts_month'),
        param=(m.ts_month,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'power_price_timepoint.tab'),
        # first column must show timepoint, and other column must be named 'purchase_power_price'
        autoselect=True,
        param=(m.purchase_power_price,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'nonenergy_price_timepoint.tab'),
        # first column must show timepoint, and other column must be named 'nonenergy_price'
        autoselect=True,
        param=(m.nonenergy_price,)
    )
    switch_data.load_aug(
        optional=True,
        filename=os.path.join(inputs_dir, 'demand_charge_period.tab'),
        # first column must show period, and other column must be named 'demand_charge'
        autoselect=True,
        param=(m.demand_charge,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'ppa_price_timepoint.tab'),
        auto_select=True,
        param=(m.ppa_price,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'generation_projects_info.tab'),
        auto_select=True,
        param=(m.gen_is_ppa)
    )
    switch_data.load_aug(
        filename = os.path.join(inputs_dir, 'cooling_demand.tab'),
        auto_select=True,
        param=(m.cooling_demand)
    )


def post_solve(instance, outdir):
    import switch_model.reporting as reporting

    reporting.write_table(
        instance, instance.TIMEPOINTS,
        output_file=os.path.join(outdir, "cost_timepointweighted.txt"),
        headings=("timestamp",)+tuple(instance.Cost_Components_Per_TP),
        values=lambda m, tp : (m.tp_ts[tp],) + tuple(
            getattr(m, component) [tp] * m.tp_weight_in_year[tp]
            for component in (m.Cost_Components_Per_TP)))

    reporting.write_table(
        instance, instance.PERIODS,
        output_file=os.path.join(outdir, "cost_period.txt"),
        headings=("period",)+tuple(instance.Cost_Components_Per_TP)+tuple(instance.Cost_Components_Per_Period),
        values=lambda m, p : (m.period_start[p],) +
        tuple(
            sum(getattr(m, component) [tp] * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p]) *
            m.bring_annual_costs_to_base_year[p]
            for component in (m.Cost_Components_Per_TP)) +
        tuple(
            getattr(m, component) [p] * m.bring_annual_costs_to_base_year[p]
            for component in (m.Cost_Components_Per_Period)))

    reporting.write_table(
        instance, instance.PERIODS,
        output_file=os.path.join(outdir, "gen_capacity_built_period.txt"),
        headings=("period",)+tuple(sorted(instance.GENERATION_PROJECTS)),
        values=lambda m, p: (m.period_start[p],) +
        tuple(m.GenCapacity[g, p] if (g, p) in m.GEN_PERIODS
            else 0.0
            for g in sorted(m.GENERATION_PROJECTS)))

    reporting.write_table(
        instance, instance.PERIODS,
        output_file=os.path.join(outdir, "gen_cost_built_period.txt"),
        headings=("period",)+tuple(sorted(instance.GENERATION_PROJECTS)),
        values=lambda m, p: (m.period_start[p],) +
        tuple((m.GenCapitalCosts[g, p] + m.GenFixedOMCosts[g, p]) * m.bring_annual_costs_to_base_year[p]
            if (g, p) in m.GEN_PERIODS
            else 0.0
            for g in sorted(m.GENERATION_PROJECTS)))

    reporting.write_table(
        instance, instance.TIMESERIES,
        output_file=os.path.join(outdir, "cost_ts.txt"),
        headings=("timeseries",)+tuple(instance.Cost_Components_Per_TP),
        values=lambda m, ts : (m.ts_month[ts],) + tuple(
            sum(getattr(m, component) [tp] * m.tp_weight_in_year[tp] for tp in m.TIMEPOINTS if m.tp_ts[tp] == ts)
            for component in (m.Cost_Components_Per_TP)))

    reporting.write_table(
        instance, instance.TIMESERIES,
        output_file=os.path.join(outdir, "dispatch_ts_weighted.txt"),
        headings=("timeseries",)+tuple(sorted(instance.GENERATION_PROJECTS)),
        values=lambda m, ts: (m.ts_month[ts],) + tuple(
            sum(m.DispatchGen[p, tp] if (p, tp) in m.GEN_TPS
            else 0.0
            for tp in m.TIMEPOINTS if m.tp_ts[tp] == ts)
            for p in sorted(m.GENERATION_PROJECTS)
        )
    )
