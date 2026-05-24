-- Portfolio SQL examples for a football scouting analytics review.
-- These checks assume the generated CSVs are loaded as warehouse tables.

-- 1. Confirm every scouting output has a source player profile.
select
  q.player_id,
  q.player_name
from scouting_priority_queue q
left join player_match_features f
  on q.player_id = f.player_id
where f.player_id is null;

-- 2. Find high-priority rows that should be sample-risk flagged.
select
  player_name,
  team_name,
  role,
  minutes,
  review_priority,
  data_risk,
  next_action
from scouting_priority_queue
where review_priority >= 180
  and minutes < 170
order by review_priority desc;

-- 3. Validate that every player-match feature row has a role and positive minutes.
select
  count(*) as failing_rows
from player_match_features
where role is null
   or role = ''
   or minutes <= 0;

-- 4. Summarize role-level scouting distribution for stakeholder readout.
select
  role,
  count(*) as players,
  round(avg(review_priority), 1) as avg_review_priority,
  round(avg(model_probability), 3) as avg_model_probability,
  round(avg(confidence), 3) as avg_confidence
from scouting_priority_queue
group by role
order by avg_review_priority desc;

-- 5. Compare event sample coverage by match.
select
  match_date,
  home_team,
  away_team,
  event_rows,
  lineup_players
from match_manifest
order by match_date;
