const API = "/api/v1";
const dateFmt = new Intl.DateTimeFormat("en-US", { dateStyle: "short", timeStyle: "short" });
const state = {
  tab: "overview",
  filters: { segment: "", start_date: "", end_date: "" },
  leads: { limit: 40, offset: 0, sort_by: "created_at", sort_order: "desc" },
  experiments: { limit: 40, offset: 0 },
  schedulerConfig: null,
  cronSnapshot: null,
  flashTimer: null,
  expandedLeadId: null,
};

const $ = (id) => document.getElementById(id);
const esc = (v) => (v == null ? "" : String(v).replace(/[&<>"']/g, (s) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[s])));
const fmt = (iso) => {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? esc(iso) : dateFmt.format(d);
};
const rate = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : "0%");

function flash(message, type = "ok") {
  const el = $("flash");
  if (state.flashTimer) {
    clearTimeout(state.flashTimer);
    state.flashTimer = null;
  }
  el.className = `flash ${type}`;
  el.textContent = message;
  state.flashTimer = setTimeout(() => {
    clearFlash();
    state.flashTimer = null;
  }, 4500);
}

function clearFlash() {
  const el = $("flash");
  el.className = "flash";
  el.textContent = "";
}

async function api(path, options = {}) {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : {};
  if (!res.ok) {
    throw new Error(data?.detail || `HTTP ${res.status}`);
  }
  return data;
}

function qs(obj) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== "" && v != null) q.set(k, v);
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

function setTab(tab) {
  state.tab = tab;
  clearFlash();
  document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === tab));
  if (tab === "scheduler") loadScheduler();
  if (tab === "leads") loadLeads();
  if (tab === "experiments") loadExperiments();
  if (tab === "activity") loadActivity();
}

async function loadSegments() {
  const segments = await api("/leads/segments");
  const sources = await api("/leads/sources");
  const select = $("filter-segment");
  const list = $("segments-list");
  const sourceList = $("sources-list");
  const expSegment = $("ab-segment");
  select.innerHTML = `<option value="">All segments</option>${segments.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
  list.innerHTML = segments.map((s) => `<option value="${esc(s)}"></option>`).join("");
  if (expSegment) {
    expSegment.innerHTML = `<option value="">Select segment</option>${segments.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
  }
  const sourceDefaults = ["website", "manual", "import", "referral", "linkedin", "other"];
  const allSources = [...new Set([...sourceDefaults, ...sources])];
  sourceList.innerHTML = allSources.map((s) => `<option value="${esc(s)}"></option>`).join("");
}

async function loadExperimentOptions() {
  const opts = await api("/experiments/options");
  const angles = opts.messaging_angles || [];
  const formats = opts.email_formats || [];
  const languages = opts.languages || [];
  $("ab-angle-a").innerHTML = `<option value="">Select messaging angle</option>${angles.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
  $("ab-angle-b").innerHTML = `<option value="">Select messaging angle</option>${angles.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
  $("ab-format-a").innerHTML = `<option value="">Select email format</option>${formats.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
  $("ab-format-b").innerHTML = `<option value="">Select email format</option>${formats.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
  $("ab-language-a").innerHTML = `<option value="">Select language</option>${languages.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
  $("ab-language-b").innerHTML = `<option value="">Select language</option>${languages.map((s) => `<option value="${esc(s)}">${esc(s)}</option>`).join("")}`;
}

async function loadOverview() {
  const q = qs(state.filters);
  const [summary, segments, recent, cron] = await Promise.all([
    api(`/analytics/summary${q}`),
    api(`/analytics/segments${q}`),
    api(`/analytics/recent-emails?limit=12${q ? `&${q.slice(1)}` : ""}`),
    api(`/analytics/cron-status`),
  ]);

  $("kpi-sent").textContent = summary.sent;
  $("kpi-written").textContent = summary.written_emails ?? 0;
  $("kpi-opened").textContent = summary.opened;
  $("kpi-replied").textContent = summary.replied;
  $("kpi-open-rate").textContent = rate(summary.opened, summary.sent);

  const maxSent = Math.max(1, ...segments.map((s) => Number(s.sent || 0)));
  $("overview-segments").innerHTML = segments.length
    ? segments
        .map(
          (s) => `
      <div class="segment-line">
        <div>
          <div>${esc(s.segment)}</div>
          <div class="hint" style="margin:2px 0 0">${esc(s.sent)} sent · ${esc(s.opened)} opened · ${esc(s.replied)} replied</div>
        </div>
        <div class="bar"><i style="width:${Math.max(6, Math.round((Number(s.sent || 0) / maxSent) * 100))}%"></i></div>
      </div>
    `
        )
        .join("")
    : '<p class="hint">No segment data for this filter.</p>';

  $("overview-recent").innerHTML = recent.length
    ? recent
        .map(
          (r) => `
      <tr>
        <td>${esc(r.company)}</td>
        <td class="mono">${esc(r.contact_email)}</td>
        <td>${esc(r.segment)}</td>
        <td>${fmt(r.sent_at)}</td>
      </tr>
    `
        )
        .join("")
    : '<tr><td colspan="4">No sent emails found.</td></tr>';

  state.cronSnapshot = cron;
  paintCronBadge();
}

function paintCronBadge() {
  const cron = state.cronSnapshot;
  if (!cron) return;
  const dot = $("cron-dot");
  dot.className = "dot";
  if (cron.status === "running") dot.classList.add("ok");
  if (cron.status === "error" || cron.status === "paused") dot.classList.add("err");
  const heartbeat = cron.last_heartbeat ? fmt(cron.last_heartbeat) : "-";
  const statusLabel =
    cron.status === "running" ? "Running"
    : cron.status === "waiting" ? "Waiting"
    : cron.status === "paused" ? "Paused"
    : cron.status === "error" ? "Error"
    : "Stale";
  $("cron-label").textContent = `Scheduler ${statusLabel} · heartbeat ${heartbeat}`;
}

async function refreshSchedulerState() {
  const [cfg, snapshot] = await Promise.all([api("/scheduler/config"), api("/analytics/cron-status")]);
  state.schedulerConfig = cfg;
  state.cronSnapshot = snapshot;
  paintCronBadge();
  return { cfg, snapshot };
}

async function loadScheduler() {
  const [{ cfg, snapshot }, queue] = await Promise.all([
    refreshSchedulerState(),
    api("/analytics/queue?limit=12"),
  ]);
  $("scheduler-enabled").value = String(cfg.enabled);
  $("scheduler-interval").value = String(cfg.min_interval_minutes);
  $("scheduler-log-level").value = cfg.log_level;
  $("scheduler-log-path").value = cfg.log_file_path;

  const snapshotStatus =
    snapshot.status === "running" ? "Running"
    : snapshot.status === "waiting" ? "Waiting"
    : snapshot.status === "paused" ? "Paused"
    : snapshot.status === "error" ? "Error"
    : "Stale";
  $("scheduler-status").textContent = snapshotStatus;
  $("scheduler-last-heartbeat").textContent = fmt(snapshot.last_heartbeat);
  $("scheduler-last-event").textContent = snapshot.last_event?.event || "-";
  $("scheduler-last-sent").textContent = fmt(snapshot.last_sent_at);
  $("scheduler-next-heartbeat").textContent =
    snapshot.status === "running" || snapshot.status === "waiting"
      ? fmt(snapshot.next_planned_heartbeat)
      : "-";
  $("scheduler-queue-rows").innerHTML = queue.length
    ? queue
        .map(
          (q) => `
      <tr>
        <td>${q.position}</td>
        <td>${esc(q.ab_test_name)} <span class="hint" style="display:block;margin:0">#${q.ab_test_id} · ${esc(q.segment)}/${esc(q.country)}</span></td>
        <td>${esc(q.company)} <span class="hint mono" style="display:block;margin:0">#${q.lead_id}</span></td>
        <td>${esc(q.side)}</td>
        <td>${esc(q.messaging_angle)}</td>
        <td>${esc(q.language)}</td>
      </tr>
    `
        )
        .join("")
    : '<tr><td colspan="6">No queued emails.</td></tr>';
}

function syncLeadSortButtons() {
  document.querySelectorAll("[data-lead-sort]").forEach((btn) => {
    const field = btn.dataset.leadSort;
    const active = state.leads.sort_by === field;
    const arrow = active ? (state.leads.sort_order === "asc" ? " ▲" : " ▼") : "";
    const label = field.charAt(0).toUpperCase() + field.slice(1);
    btn.textContent = `${label}${arrow}`;
    btn.classList.toggle("primary", active);
  });
}

async function loadLeads() {
  const { limit, offset, sort_by, sort_order } = state.leads;
  const leads = await api(
    `/leads?limit=${limit}&offset=${offset}&sort_by=${encodeURIComponent(sort_by)}&sort_order=${encodeURIComponent(sort_order)}`
  );
  $("leads-rows").innerHTML = leads.length
    ? leads
        .map(
          (l) => `
      <tr>
        <td>${esc(l.company)}</td>
        <td>${esc(l.segment)}</td>
        <td>${esc(l.status)}</td>
        <td><button class="btn" data-lead-edit="${l.lead_id}">Edit</button></td>
      </tr>
      <tr id="lead-expand-${l.lead_id}" style="display:none">
        <td colspan="4">
          <div class="lead-detail-wrap">
            <div class="form-grid">
              <div class="field"><label>Company</label><input data-lead-company="${l.lead_id}" value="${esc(l.company)}" /></div>
              <div class="field"><label>Contact email</label><input data-lead-email="${l.lead_id}" value="${esc(l.contact_email)}" /></div>
              <div class="field"><label>Website</label><input data-lead-website="${l.lead_id}" value="${esc(l.website)}" /></div>
              <div class="field"><label>Segment</label><input data-lead-segment="${l.lead_id}" value="${esc(l.segment)}" /></div>
              <div class="field"><label>Industry</label><input data-lead-industry="${l.lead_id}" value="${esc(l.industry || "")}" /></div>
              <div class="field"><label>Country</label><input data-lead-country="${l.lead_id}" value="${esc(l.country || "")}" /></div>
              <div class="field"><label>Source</label><input data-lead-source="${l.lead_id}" list="sources-list" value="${esc(l.source || "")}" /></div>
              <div class="field">
                <label>Status</label>
                <select data-lead-status="${l.lead_id}">
                  <option value="new" ${l.status === "new" ? "selected" : ""}>new</option>
                  <option value="written" ${l.status === "written" ? "selected" : ""}>written</option>
                  <option value="contacted" ${l.status === "contacted" ? "selected" : ""}>contacted</option>
                </select>
              </div>
              <div class="full row-actions">
                <button class="btn primary" data-lead-save="${l.lead_id}">Save</button>
                <button class="btn" data-lead-cancel="${l.lead_id}">Cancel</button>
              </div>
            </div>
          </div>
        </td>
      </tr>
    `
        )
        .join("")
    : '<tr><td colspan="4">No leads yet.</td></tr>';
  const page = Math.floor(offset / limit) + 1;
  $("leads-page").textContent = `Page ${page}`;
  $("leads-prev").disabled = offset === 0;
  $("leads-next").disabled = leads.length < limit;
  syncLeadSortButtons();

  document.querySelectorAll("[data-lead-edit]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-lead-edit");
      if (state.expandedLeadId && state.expandedLeadId !== id) {
        const prev = document.getElementById(`lead-expand-${state.expandedLeadId}`);
        if (prev) prev.style.display = "none";
      }
      const row = document.getElementById(`lead-expand-${id}`);
      if (!row) return;
      const isOpen = row.style.display !== "none";
      row.style.display = isOpen ? "none" : "";
      state.expandedLeadId = isOpen ? null : id;
    });
  });

  document.querySelectorAll("[data-lead-cancel]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-lead-cancel");
      const row = document.getElementById(`lead-expand-${id}`);
      if (row) row.style.display = "none";
      state.expandedLeadId = null;
      await loadLeads();
    });
  });

  document.querySelectorAll("[data-lead-save]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-lead-save");
      const status = document.querySelector(`[data-lead-status=\"${id}\"]`).value;
      const segment = document.querySelector(`[data-lead-segment=\"${id}\"]`).value.trim();
      const company = document.querySelector(`[data-lead-company=\"${id}\"]`).value.trim();
      const contact_email = document.querySelector(`[data-lead-email=\"${id}\"]`).value.trim();
      const website = document.querySelector(`[data-lead-website=\"${id}\"]`).value.trim();
      const industry = document.querySelector(`[data-lead-industry=\"${id}\"]`).value.trim();
      const country = document.querySelector(`[data-lead-country=\"${id}\"]`).value.trim();
      const source = document.querySelector(`[data-lead-source=\"${id}\"]`).value.trim();
      btn.disabled = true;
      try {
        await api(`/leads/${id}`, {
          method: "PATCH",
          body: JSON.stringify({
            company,
            contact_email,
            website,
            segment,
            industry: industry || null,
            country: country || null,
            source: source || null,
            status,
          }),
        });
        flash(`Lead #${id} updated.`);
        state.expandedLeadId = null;
        await Promise.all([loadLeads(), loadSegments(), loadOverview()]);
      } catch (e) {
        flash(e.message, "err");
      } finally {
        btn.disabled = false;
      }
    });
  });
}

async function loadExperiments() {
  const { limit, offset } = state.experiments;
  const exps = await api(`/ab-tests?limit=${limit}&offset=${offset}&sort_by=created_at&sort_order=desc`);
  const rows = await Promise.all(
    exps.map(async (e) => {
      const r = await api(`/ab-tests/${e.ab_test_id}/results`);
      return { e, r };
    })
  );
  $("exp-rows").innerHTML = rows.length
    ? rows.map(({ e, r }) => `
      <tr>
        <td>${e.ab_test_id}</td>
        <td>${esc(e.name)}</td>
        <td>${esc(e.segment)}</td>
        <td>${esc(e.country)}</td>
        <td>${e.max_emails_total}</td>
        <td>${r.sent_a}/${r.sent_b}</td>
        <td>${Math.round((r.reply_rate_a || 0) * 100)}% / ${Math.round((r.reply_rate_b || 0) * 100)}%</td>
        <td>${esc(r.winner_side)}</td>
        <td>${Number(e.active) === 1 ? "true" : "false"}</td>
      </tr>
    `).join("")
    : '<tr><td colspan="9">No A/B tests yet.</td></tr>';
  const page = Math.floor(offset / limit) + 1;
  $("exp-page").textContent = `Page ${page}`;
  $("exp-prev").disabled = offset === 0;
  $("exp-next").disabled = rows.length < limit;
}

async function loadActivity() {
  const activity = await api("/analytics/activity?limit=40");
  $("activity-scheduler-main").innerHTML = activity.scheduler_events_main.length
    ? activity.scheduler_events_main
        .map(
          (e) => `
      <tr>
        <td class="mono">${esc(e.timestamp)}</td>
        <td>${esc(e.event || "-")}</td>
        <td class="mono">${esc(JSON.stringify(e.detail || {}))}</td>
      </tr>
    `
        )
        .join("")
    : '<tr><td colspan="3">No scheduler events found.</td></tr>';
  $("activity-scheduler-test").innerHTML = activity.scheduler_events_test.length
    ? activity.scheduler_events_test
        .map(
          (e) => `
      <tr>
        <td class="mono">${esc(e.timestamp)}</td>
        <td>${esc(e.event || "-")}</td>
        <td class="mono">${esc(JSON.stringify(e.detail || {}))}</td>
      </tr>
    `
        )
        .join("")
    : '<tr><td colspan="3">No test scheduler events found.</td></tr>';

  $("activity-emails").innerHTML = activity.email_events.length
    ? activity.email_events
        .map(
          (e) => `
      <tr>
        <td class="mono">${fmt(e.event_time)}</td>
        <td>${esc(e.event_type)}</td>
        <td>${esc(e.company)} <span class="hint" style="display:block;margin:0">#${e.lead_id} · ${esc(e.segment)}</span></td>
      </tr>
    `
        )
        .join("")
    : '<tr><td colspan="3">No email events found.</td></tr>';
}

async function saveSchedulerConfig() {
  const btn = $("scheduler-save");
  btn.disabled = true;
  clearFlash();
  try {
    const payload = {
      enabled: $("scheduler-enabled").value === "true",
      min_interval_minutes: Number($("scheduler-interval").value),
      log_level: $("scheduler-log-level").value,
      log_file_path: $("scheduler-log-path").value.trim(),
    };
    await api("/scheduler/config", { method: "PATCH", body: JSON.stringify(payload) });
    flash("Scheduler config updated.");
    await Promise.all([loadScheduler(), loadOverview(), loadActivity()]);
  } catch (e) {
    flash(e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function runScheduler(mode) {
  const isTest = mode === "test";
  const btn = isTest ? $("scheduler-test") : $("scheduler-restart");
  btn.disabled = true;
  clearFlash();
  try {
    const out = await api("/scheduler/run", { method: "POST", body: JSON.stringify({ mode, dry_run: isTest }) });
    flash(`Run finished: ok=${out.ok}, exit_code=${out.exit_code}, mode=${out.mode}, dry_run=${out.dry_run}`);
    await Promise.all([loadScheduler(), loadOverview(), loadActivity()]);
  } catch (e) {
    flash(e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function createLead() {
  const btn = $("lead-create");
  btn.disabled = true;
  clearFlash();
  try {
    const payload = {
      company: $("lead-company").value.trim(),
      contact_email: $("lead-email").value.trim(),
      website: $("lead-website").value.trim(),
      segment: $("lead-segment").value.trim(),
      industry: $("lead-industry").value.trim() || null,
      country: $("lead-country").value.trim() || null,
      source: $("lead-source").value.trim() || null,
      status: $("lead-status").value,
    };
    if (!payload.company || !payload.contact_email || !payload.website || !payload.segment) {
      throw new Error("Company, contact email, website and segment are required.");
    }
    await api("/leads", { method: "POST", body: JSON.stringify(payload) });
    flash("Lead created.");
    ["lead-company","lead-email","lead-website","lead-segment","lead-industry","lead-country","lead-source"].forEach((id) => ($(id).value = ""));
    $("lead-status").value = "new";
    state.leads.offset = 0;
    await Promise.all([loadLeads(), loadSegments(), loadOverview()]);
  } catch (e) {
    flash(e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

async function createExperiment() {
  const btn = $("exp-create");
  btn.disabled = true;
  clearFlash();
  try {
    const payload = {
      name: $("ab-name").value.trim(),
      segment: $("ab-segment").value.trim(),
      country: $("ab-country").value.trim(),
      comparison_mode: $("ab-mode").value.trim(),
      changed_dimensions: $("ab-dimensions").value
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean),
      max_emails_total: Number($("ab-max-emails").value),
      active: $("exp-active").value === "true",
      variant_a: {
        messaging_angle: $("ab-angle-a").value.trim(),
        email_format: $("ab-format-a").value.trim(),
        subject_variant: $("ab-subject-a").value.trim() || null,
        language: $("ab-language-a").value.trim() || "en",
      },
      variant_b: {
        messaging_angle: $("ab-angle-b").value.trim(),
        email_format: $("ab-format-b").value.trim(),
        subject_variant: $("ab-subject-b").value.trim() || null,
        language: $("ab-language-b").value.trim() || "en",
      },
    };
    if (
      !payload.name ||
      !payload.segment ||
      !payload.country ||
      !payload.comparison_mode ||
      !payload.max_emails_total ||
      !payload.variant_a.messaging_angle ||
      !payload.variant_a.email_format ||
      !payload.variant_b.messaging_angle ||
      !payload.variant_b.email_format
    ) {
      throw new Error("Name, segment, country, mode, max_emails_total and both variants are required.");
    }
    await api("/ab-tests", { method: "POST", body: JSON.stringify(payload) });
    flash("A/B test created.");
    [
      "ab-name","ab-segment","ab-country","ab-mode","ab-dimensions","ab-max-emails",
      "ab-angle-a","ab-format-a","ab-subject-a","ab-language-a",
      "ab-angle-b","ab-format-b","ab-subject-b","ab-language-b",
    ].forEach((id) => ($(id).value = ""));
    $("exp-active").value = "true";
    state.experiments.offset = 0;
    await Promise.all([loadExperiments(), loadSegments(), loadOverview()]);
  } catch (e) {
    flash(e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

function bindEvents() {
  document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => setTab(t.dataset.tab)));

  $("overview-apply").addEventListener("click", async () => {
    state.filters.segment = $("filter-segment").value;
    state.filters.start_date = $("filter-start").value;
    state.filters.end_date = $("filter-end").value;
    await loadOverview();
  });

  $("overview-reset").addEventListener("click", async () => {
    $("filter-segment").value = "";
    $("filter-start").value = "";
    $("filter-end").value = "";
    state.filters = { segment: "", start_date: "", end_date: "" };
    await loadOverview();
  });

  $("scheduler-save").addEventListener("click", saveSchedulerConfig);
  $("scheduler-restart").addEventListener("click", () => runScheduler("live"));
  $("scheduler-test").addEventListener("click", () => runScheduler("test"));

  $("lead-create").addEventListener("click", createLead);
  $("leads-refresh").addEventListener("click", loadLeads);
  $("leads-prev").addEventListener("click", async () => {
    state.leads.offset = Math.max(0, state.leads.offset - state.leads.limit);
    await loadLeads();
  });
  $("leads-next").addEventListener("click", async () => {
    state.leads.offset += state.leads.limit;
    await loadLeads();
  });
  document.querySelectorAll("[data-lead-sort]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const field = btn.dataset.leadSort;
      if (state.leads.sort_by === field) {
        state.leads.sort_order = state.leads.sort_order === "asc" ? "desc" : "asc";
      } else {
        state.leads.sort_by = field;
        state.leads.sort_order = "asc";
      }
      state.leads.offset = 0;
      await loadLeads();
    });
  });

  $("exp-create").addEventListener("click", createExperiment);
  $("exp-refresh").addEventListener("click", loadExperiments);
  $("exp-prev").addEventListener("click", async () => {
    state.experiments.offset = Math.max(0, state.experiments.offset - state.experiments.limit);
    await loadExperiments();
  });
  $("exp-next").addEventListener("click", async () => {
    state.experiments.offset += state.experiments.limit;
    await loadExperiments();
  });
}

async function boot() {
  bindEvents();
  try {
    await loadSegments();
    await loadExperimentOptions();
    await Promise.all([loadOverview(), refreshSchedulerState()]);
  } catch (e) {
    flash(e.message, "err");
  }
}

boot();
