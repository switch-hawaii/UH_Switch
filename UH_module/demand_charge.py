import os
from pyomo.environ import *

def define_components(m):
    m.ts_month = Param(m.TIMESERIES)
    m.MONTHS = Set(initialize=lambda m:
        sorted(set(m.ts_month[ts] for ts in m.TIMESERIES))
    )

    # price of buying or selling power (per MWh) during each timepoint (from 'power_price_timepoint.tab')
    m.purchase_power_price = Param(m.TIMEPOINTS)
    # demand charges per peak MW during each period (from 'power_price_period.tab')
    m.demand_charge = Param(m.PERIODS)
    m.nonenergy_price = Param(m.TIMEPOINTS)

    # variables for amount of power bought (supplied from outside) and sold (delivered to outside)
    m.PurchasePower = Var(m.TIMEPOINTS, within=NonNegativeReals)


    # peak power variables
    m.MonthlyPeakPurchasedPower = Var(m.PERIODS, m.MONTHS, within=NonNegativeReals)
    m.AnnualPeakPurchasedPower = Var(m.PERIODS, within=NonNegativeReals)


    # force these to take the right values
    m.Calculate_MonthlyPeakPurchasedPower = Constraint(m.TIMEPOINTS, rule=lambda m, tp:
        m.MonthlyPeakPurchasedPower[m.tp_period[tp], m.ts_month[m.tp_ts[tp]]]
        >=
        m.PurchasePower[tp]
    )

    m.Calculate_AnnualPeakPurchasedPower = Constraint(m.PERIODS, m.MONTHS, rule=lambda m, p, mo:
        m.AnnualPeakPurchasedPower[p]
        >=
        m.MonthlyPeakPurchasedPower[p, mo]
    )
   #above 10 lines of code calculate MonthlyPeakPruchasePowr and AnnualPeakPurchasedPower


    # add purchases and sales to model's load balance
    # use same values in all zones (should only be one zone!)
    m.PurchasePowerZone = Expression(m.LOAD_ZONES, m.TIMEPOINTS, rule=lambda m, z, tp: m.PurchasePower[tp])
    # add PurchasePower to list of sources available to satisfy demand (along with any on-site generation)
    m.Zone_Power_Injections.append('PurchasePowerZone')
    # Above lines let calculate the amount of PurchasePower in each timepoint

    # cost and revenue from power purchases and sales during each timepoint
    m.PurchasedPowerCost = Expression(
        m.TIMEPOINTS, rule=lambda m, tp: m.PurchasePower[tp] * m.purchase_power_price[tp]
    )
    m.Cost_Components_Per_TP.append('PurchasedPowerCost')

    m.NonEnergyCharge = Expression(
        m.TIMEPOINTS, rule=lambda m, tp:
        m.PurchasePower[tp] * m.nonenergy_price[tp])
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
    # annual peak is 17.27784
    #m.Force_battery=Constraint(rule=lambda m:m.DispatchGen["Battery_Storage",258]==3)


def load_inputs(m, switch_data, inputs_dir):
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'timeseries.csv'),
        select=('TIMESERIES', 'ts_month'),
        param=(m.ts_month,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'power_price_timepoint.csv'),
        # first column must show timepoint, and other column must be named 'purchase_power_price'
        autoselect=True,
        param=(m.purchase_power_price,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'nonenergy_price_timepoint.csv'),
        # first column must show timepoint, and other column must be named 'nonenergy_price'
        autoselect=True,
        param=(m.nonenergy_price,)
    )
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'demand_charge_period.csv'),
        # first column must show period, and other column must be named 'demand_charge'
        autoselect=True,
        param=(m.demand_charge,)
    )

def post_solve(instance, outdir):
    import switch_model.reporting as reporting

    reporting.write_table(
        instance, instance.TIMEPOINTS,
        output_file=os.path.join(outdir, "cost_timepointweighted.csv"),
        headings=("timestamp",)+tuple(instance.Cost_Components_Per_TP),
        values=lambda m, tp : (m.tp_ts[tp],) + tuple(
            getattr(m, component) [tp] * m.tp_weight_in_year[tp]
            for component in (m.Cost_Components_Per_TP)))

    reporting.write_table(
        instance, instance.PERIODS,
        output_file=os.path.join(outdir, "cost_period.csv"),
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
        output_file=os.path.join(outdir, "gen_capacity_built_period.csv"),
        headings=("period",)+tuple(sorted(instance.GENERATION_PROJECTS)),
        values=lambda m, p: (m.period_start[p],) +
        tuple(m.GenCapacity[g, p] if (g, p) in m.GEN_PERIODS
            else 0.0
            for g in sorted(m.GENERATION_PROJECTS)))

    reporting.write_table(
        instance, instance.PERIODS,
        output_file=os.path.join(outdir, "gen_cost_built_period.csv"),
        headings=("period",)+tuple(sorted(instance.GENERATION_PROJECTS)),
        values=lambda m, p: (m.period_start[p],) +
        tuple((m.GenCapitalCosts[g, p] + m.GenFixedOMCosts[g, p]) * m.bring_annual_costs_to_base_year[p]
            if (g, p) in m.GEN_PERIODS
            else 0.0
            for g in sorted(m.GENERATION_PROJECTS)))

    reporting.write_table(
        instance, instance.TIMESERIES,
        output_file=os.path.join(outdir, "cost_ts.csv"),
        headings=("timeseries",)+tuple(instance.Cost_Components_Per_TP),
        values=lambda m, ts : (m.ts_month[ts],) + tuple(
            sum(getattr(m, component) [tp] * m.tp_weight_in_year[tp] for tp in m.TIMEPOINTS if m.tp_ts[tp] == ts)
            for component in (m.Cost_Components_Per_TP)))

#    reporting.write_table(
#        instance, instance.TIMESERIES,
#        output_file=os.path.join(outdir, "cost_ts.csv"),
#        headings=("timeseries",)+tuple(instance.Cost_Components_Per_TP),
#        values=lambda m, ts : (m.ts_month[ts],) + tuple(
#            sum(getattr(m, component) [tp] * m.bring_timepoint_costs_to_base_year[tp] for tp in m.TIMEPOINTS if m.tp_ts[tp] == ts)
#            for component in (m.Cost_Components_Per_TP)))

    reporting.write_table(
        instance, instance.TIMESERIES,
        output_file=os.path.join(outdir, "dispatch_ts_weighted.csv"),
        headings=("timeseries",)+tuple(sorted(instance.GENERATION_PROJECTS)),
        values=lambda m, ts: (m.ts_month[ts],) + tuple(
            sum(m.DispatchGen[p, tp] if (p, tp) in m.GEN_TPS
            else 0.0
            for tp in m.TIMEPOINTS if m.tp_ts[tp] == ts)
            for p in sorted(m.GENERATION_PROJECTS)
        )
    )
