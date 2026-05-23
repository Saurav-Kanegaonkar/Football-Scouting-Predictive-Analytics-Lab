-- Priority queue foundation
select
  entity_id,
  avg(risk_score) as avg_risk_score,
  avg(quality_score) as avg_quality_score,
  sum(value_pool) as value_pool
from daily_metrics
group by 1
order by avg_risk_score desc;

-- Action readiness
select
  action_type,
  avg(expected_lift_pct) as expected_lift,
  avg(effort_hours) as effort_hours
from recommended_actions
group by 1;
