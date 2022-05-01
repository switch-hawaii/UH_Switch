import os
from pyomo.environ import *

def define_components(m):
    m.ts_month = Param(m.TIMESERIES)
    
def load_inputs(m, switch_data, inputs_dir):
    switch_data.load_aug(
        filename=os.path.join(inputs_dir, 'timeseries.tab'),
        select=('TIMESERIES', 'ts_month'),
        param=(m.ts_month,)
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





