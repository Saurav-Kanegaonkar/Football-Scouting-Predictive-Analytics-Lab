const state = {
  payload: null,
  selectedPlayerId: null,
  role: "All",
};

const formatPct = (value) => `${Math.round(value * 100)}%`;
const formatNumber = (value) => Number(value).toLocaleString("en-US");

async function loadPayload() {
  const response = await fetch("analysis/outputs/app_payload.json");
  state.payload = await response.json();
  state.selectedPlayerId = state.payload.players[0].player_id;
  render();
}

function render() {
  renderHero();
  renderMetrics();
  renderRoleFilter();
  renderPlayerRows();
  renderModelLab();
  renderBriefs();
  bindTabs();
}

function renderHero() {
  const { summary } = state.payload;
  document.querySelector("#topPlayer").textContent = summary.top_player;
  document.querySelector("#topContext").textContent = `${summary.top_priority} review priority across ${summary.shortlist_players} scored players.`;
}

function renderMetrics() {
  const { summary } = state.payload;
  const metrics = [
    ["Public matches", summary.matches, "StatsBomb MLS sample"],
    ["Event rows", formatNumber(summary.event_rows), "real event stream"],
    ["Modeled rows", summary.modeled_rows, "future-fit labels"],
    ["Holdout Brier", summary.holdout_brier, "calibration proxy"],
  ];
  document.querySelector("#metricGrid").innerHTML = metrics
    .map(([label, value, context]) => `
      <article>
        <span>${label}</span>
        <strong>${value}</strong>
        <em>${context}</em>
      </article>
    `)
    .join("");
}

function renderRoleFilter() {
  const select = document.querySelector("#roleFilter");
  const roles = ["All", ...new Set(state.payload.players.map((player) => player.role))].sort((a, b) => {
    if (a === "All") return -1;
    if (b === "All") return 1;
    return a.localeCompare(b);
  });
  select.innerHTML = roles.map((role) => `<option value="${role}">${role}</option>`).join("");
  select.value = state.role;
  select.addEventListener("change", (event) => {
    state.role = event.target.value;
    const players = filteredPlayers();
    state.selectedPlayerId = players[0]?.player_id ?? state.payload.players[0].player_id;
    renderPlayerRows();
  });
}

function filteredPlayers() {
  if (state.role === "All") return state.payload.players;
  return state.payload.players.filter((player) => player.role === state.role);
}

function renderPlayerRows() {
  const players = filteredPlayers();
  document.querySelector("#playerRows").innerHTML = players
    .map((player) => `
      <tr class="${player.player_id === state.selectedPlayerId ? "selected" : ""}" data-player-id="${player.player_id}">
        <td>
          <button type="button">${player.player_name}</button>
          <span>${player.team_name}</span>
        </td>
        <td>${player.role}</td>
        <td><strong>${player.review_priority}</strong></td>
        <td>${formatPct(player.model_probability)}</td>
        <td><mark class="${player.data_risk}">${player.next_action}</mark></td>
      </tr>
    `)
    .join("");
  document.querySelectorAll("#playerRows tr").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedPlayerId = Number(row.dataset.playerId);
      renderPlayerRows();
    });
  });
  renderPlayerDetail();
}

function renderPlayerDetail() {
  const player = state.payload.players.find((item) => item.player_id === state.selectedPlayerId) || filteredPlayers()[0];
  if (!player) return;
  const metrics = [
    ["xG p90", player.xg_p90],
    ["Prog pass p90", player.progressive_passes_p90],
    ["Prog carry p90", player.progressive_carries_p90],
    ["Pressures p90", player.pressures_p90],
    ["Def actions p90", player.defensive_actions_p90],
    ["Turnovers p90", player.turnovers_p90],
  ];
  document.querySelector("#playerDetail").innerHTML = `
    <p class="eyebrow">Selected profile</p>
    <h3>${player.player_name}</h3>
    <p>${player.position} for ${player.team_name}. ${player.squad_phase}, ${player.minutes} modeled minutes, ${player.data_risk} data risk.</p>
    <div class="score-ring">
      <span>${player.review_priority}</span>
      <small>review priority</small>
    </div>
    <div class="detail-grid">
      ${metrics.map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join("")}
    </div>
  `;
}

function renderModelLab() {
  const metrics = state.payload.model_metrics;
  const metricRows = [
    ["Holdout rows", metrics.rows],
    ["Accuracy", formatPct(metrics.accuracy)],
    ["Precision", formatPct(metrics.precision)],
    ["Recall", formatPct(metrics.recall)],
    ["Positive rate", formatPct(metrics.positive_rate)],
    ["Brier score", metrics.brier],
  ];
  document.querySelector("#diagnostics").innerHTML = metricRows
    .map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`)
    .join("");

  const maxWeight = Math.max(...state.payload.feature_importance.map((item) => Math.abs(item.weight)));
  document.querySelector("#importance").innerHTML = state.payload.feature_importance.slice(0, 8)
    .map((item) => `
      <div class="feature-row">
        <span>${item.feature.replaceAll("_", " ")}</span>
        <div><i style="width:${Math.max(8, Math.abs(item.weight) / maxWeight * 100)}%"></i></div>
        <strong>${item.weight}</strong>
      </div>
    `)
    .join("");

  const maxPriority = Math.max(...state.payload.role_summary.map((role) => role.avg_priority));
  document.querySelector("#roleBars").innerHTML = state.payload.role_summary
    .map((role) => `
      <div class="role-row">
        <span>${role.role}</span>
        <div><i style="width:${role.avg_priority / maxPriority * 100}%"></i></div>
        <strong>${role.avg_priority}</strong>
        <small>${role.players} players</small>
      </div>
    `)
    .join("");
}

function renderBriefs() {
  document.querySelector("#briefList").innerHTML = state.payload.briefs
    .map((brief) => `
      <article>
        <span>${brief.role}</span>
        <h3>${brief.player_name}</h3>
        <p>${brief.brief}</p>
      </article>
    `)
    .join("");
  document.querySelector("#qualityChecks").innerHTML = state.payload.data_quality
    .map((check) => `
      <article class="quality-check">
        <mark>${check.status}</mark>
        <div>
          <h4>${check.check}</h4>
          <p>${check.result}</p>
          <small>${check.owner}</small>
        </div>
      </article>
    `)
    .join("");
}

function bindTabs() {
  document.querySelectorAll(".tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tabs button").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`#${button.dataset.view}View`).classList.add("active");
    });
  });
}

loadPayload();
