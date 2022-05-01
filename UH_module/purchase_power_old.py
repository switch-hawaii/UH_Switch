import os
from pyomo.environ import *

def define_components(m):
    m.ts_month = Param(m.TIMESERIES)
    m.MONTHS = Set(initialize=lambda m:
        sorted(set(m.ts_month[ts] for ts in m.TIMESERIES))
    )
    m.gen_is_ppa = Param(m.GENERATION_PROJECTS, within=Boolean)
    m.PPA_GENS = Set(initialize=m.GENERATION_PROJECTS, filter=lambda m, g: m.gen_is_ppa[g])
    m.PPA_GEN_TPS = Set(
        dimen=2,
        initialize=lambda m: (
            (g, tp) 
                for g in m.PPA_GENS
                    for tp in m.TPS_FOR_GEN[g]))
    m.ppa_price = Param(m.PPA_GEN_TPS, within=NonNegativeReals)
    # price of buying or selling power (per MWh) during each timepoint (from 'power_price_timepoint.tab')
    m.purchase_power_price = Param(m.TIMEPOINTS)

    m.nonenergy_price = Param(m.TIMEPOINTS)
    # demand charges per peak MW during each period (from 'power_price_period.tab')
    m.demand_charge = Param(m.PERIODS, default=0.0)

    # fixed monthly charge during each period (from 'power_price_period.tab')
    #m.fixed_charge = Param(m.PERIODS, default=0.0)
 
    
    # variables for amount of power bought (supplied from outside) and sold (delivered to outside)
    m.PurchasePower = Var(m.TIMEPOINTS, within=NonNegativeReals)
    m.PPAPurchased = Var(m.PPA_GEN_TPS, within=NonNegativeReals)

    #only purchase from PPA projects when they can generate   
    m.Limit_PPAPurchased = Constraint(
        m.PPA_GEN_TPS, 
        rule=lambda m, g, tp: 
            m.PPAPurchased[g, tp] 
            <= 
            m.gen_capacity_limit_mw[g] * (m.gen_max_capacity_factor[g, tp] if m.gen_is_variable[g] else 1.0) 
    ) 
 
    m.SellPower = Expression(m.TIMEPOINTS, rule=lambda m, tp: 
        sum(m.DispatchGen[g, tp] for g in m.PPA_GENS))

    m.PowerWH = Expression(m.LOAD_ZONES,
        m.TIMEPOINTS, 
        rule=lambda m, z, tp: 
            sum(m.GenCapacity[g, m.tp_period[tp]] * m.gen_max_capacity_factor[g, tp] for g in m.PPA_GENS) 
    )
    m.Zone_Power_Injections.append('PowerWH')
    m.Zone_Power_Withdrawals.append('PowerWH')

    
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

    # add purchases and sales to model's load balance
    # use same values in all zones (should only be one zone!)
    m.PurchasePowerZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS, rule=lambda m, z, tp: m.PurchasePower[tp])
    m.SellPowerZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS, rule=lambda m, z, tp: m.SellPower[tp])
    # add PurchasePower to list of sources available to satisfy demand (along with any on-site generation)
    m.Zone_Power_Injections.append('PurchasePowerZone')
    # add SellPower to list of loads (along with on-site loads)
    m.Zone_Power_Withdrawals.append('SellPowerZone')

    m.PPAZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS, rule=lambda m, z, tp: 
        sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS))
    m.Zone_Power_Injections.append('PPAZone')

    # fixed charge (if any), allocated to individual timepoints
    #m.FixedChargeCost = Expression(
        # note: 8760/12 is the average number of hours per month
    #    m.TIMEPOINTS, rule=lambda m, tp: m.fixed_charge[m.tp_period[tp]] * m.tp_duration_hours[tp] / (8760.0/12.0)
    #)
    #m.Cost_Components_Per_TP.append('FixedChargeCost')


    # cost and revenue from power purchases and sales during each timepoint
    m.PurchasedPowerCost = Expression(
        m.TIMEPOINTS, rule=lambda m, tp: m.PurchasePower[tp] * m.purchase_power_price[tp]
    )
    m.Cost_Components_Per_TP.append('PurchasedPowerCost')
    

    m.PPACost = Expression(
        m.TIMEPOINTS, 
        rule=lambda m, tp: 
        sum(m.PPAPurchased[g, tp] * 
            m.ppa_price[g, tp] for g in m.PPA_GENS))
    m.Cost_Components_Per_TP.append('PPACost')
    m.PPACostNeg = Expression(
        m.TIMEPOINTS, 
        rule=lambda m, tp: 
        -1* m.PPACost[tp])
    m.Cost_Components_Per_TP.append('PPACostNeg')

    m.CapacityCost = Expression(
        m.TIMEPOINTS, 
        rule=lambda m, tp: 
        sum(m.GenCapacity[g, m.tp_period[tp]] * m.gen_max_capacity_factor[g, tp] *  m.ppa_price[g, tp] for g in m.PPA_GENS))
    m.Cost_Components_Per_TP.append('CapacityCost')

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

    # if wanted, you can declare a monthly base charge for each period (stored in power_price_period.tab),
    # then read that into a parameter, create an Expression that scales it up to an annual cost, 
    # and append that expression to the m.Cost_Components_Per_Period list (each component in that
    # list is actually an annual cost).

    # m.Bound_System_Cost = Constraint(rule=lambda m: m.SystemCost >= -1e20)
    
    # total sales to HECO during each period must not exceed total purchases (net zero, but not net-negative)
    m.Net_Non_Negative = Constraint(m.PERIODS, rule=lambda m, p: 
        sum(m.SellPower[tp] * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p]) 
        <=
        sum(sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS) * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p])
    )
    m.ConstraintPPAPurchased= Constraint(m.PERIODS, rule=lambda m, p: 
        sum(sum(m.PPAPurchased[g, tp] for g in m.PPA_GENS) * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p]) 
        <= 
        (sum(m.DispatchGen[g, tp] * m.tp_weight_in_year[tp] for tp in m.TPS_IN_PERIOD[p] for g in m.PPA_GENS ))
    )



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
        index=m.GENERATION_PROJECTS,
        param=(m.gen_is_ppa)
    )

def post_solve(instance, outdir):
    import switch_mod.reporting as reporting

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





