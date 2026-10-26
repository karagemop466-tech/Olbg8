/* OLBG research desk — no framework, no third-party runtime dependencies. */
(() => {
  "use strict";

  const root = document.getElementById("app");
  const page = document.body.dataset.page || "home";
  const sportKey = document.body.dataset.sport || "";
  const BASE = page === "sport" ? "../" : "";
  const DATA_URL = `${BASE}data/dashboard.json`;

  const esc = (value) => String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

  const link = (url, label) => url
    ? `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`
    : "—";

  const safeUrl = (url) => {
    try {
      const parsed = new URL(url, window.location.href);
      return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : "";
    } catch (_) { return ""; }
  };

  const formatDate = (iso) => {
    if (!iso) return "Not stated";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return esc(iso);
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    }).format(date).replace(",", "") + " UTC";
  };

  const american = (value) => {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    if (!Number.isFinite(n)) return esc(value);
    return n > 0 ? `+${n}` : String(n);
  };

  const percent = (value) => value === null || value === undefined || value === "" ? "—" : `${esc(value)}%`;

  const badge = (value, extra = "") => {
    if (!value) return "";
    const key = String(value).toLowerCase().replace(/[^a-z]/g, "");
    const klass = key === "high" ? "high" : key === "medium" ? "medium" : key === "low" ? "low" : extra || "gray";
    return `<span class="badge ${klass}">${esc(value)}</span>`;
  };

  const statusBadge = (event) => {
    const status = event.official?.status;
    if (status === "event-confirmed") return `<span class="badge clear">event confirmed</span>`;
    if (event.research?.american !== null && event.research?.american !== undefined) {
      return `<span class="badge flag">${status === "stats-only" ? "research only" : "line, review"}</span>`;
    }
    return `<span class="badge gray">needs source match</span>`;
  };

  const typeLabel = (value) => ({ fixture: "match", race: "race", outright: "outright", unknown: "unresolved" }[value] || value || "event");

  function renderHeader() {
    const target = document.getElementById("site-header");
    if (!target) return;
    const nav = [
      ["home", "Overview", "index.html"],
      ["matches", "Matches", "matches.html"],
      ["picks", "Picks", "picks.html"],
      ["flagged", "Flagged", "flagged.html"],
      ["sources", "Sources", "sources.html"],
      ["methodology", "Method", "methodology.html"],
    ];
    target.innerHTML = `<header class="site-header"><div class="header-inner">
      <a class="brand" href="${BASE}index.html"><span class="brand-mark">O</span><span>OLBG research desk</span><span class="brand-note">source-first</span></a>
      <nav class="nav" aria-label="Primary navigation">${nav.map(([key, label, href]) => `<a class="${page === key ? "active" : ""}" href="${BASE}${href}">${label}</a>`).join("")}</nav>
    </div></header>`;
  }

  function renderFooter(data) {
    const target = document.getElementById("site-footer");
    if (!target) return;
    target.innerHTML = `<footer class="footer"><div class="footer-inner">
      <p><strong>OLBG research desk</strong> · captured ${esc(data.asOfLabel)} · ${esc(data.summary.olbgEvents)} in-scope OLBG listings.</p>
      <p class="disclaimer">Research is not a guarantee or a bookmaker offer. Blank fields are deliberate. Check the linked official source and current market before relying on any information. Only bet where lawful and only what you can afford to lose.</p>
    </div></footer>`;
  }

  function pageHead(eyebrow, title, text) {
    return `<div class="page-head"><p class="eyebrow">${esc(eyebrow)}</p><h1>${esc(title)}</h1>${text ? `<p class="lede">${esc(text)}</p>` : ""}</div>`;
  }

  function kpi(value, label, note = "") {
    return `<div class="kpi"><div class="kpi-value">${esc(value)}</div><div class="kpi-label">${esc(label)}</div>${note ? `<div class="kpi-note">${esc(note)}</div>` : ""}</div>`;
  }

  function callout(title, text, kind = "warn") {
    return `<div class="callout ${kind}"><span class="icon">${kind === "danger" ? "!" : kind === "warn" ? "i" : "✓"}</span><p><strong>${esc(title)}</strong> ${esc(text)}</p></div>`;
  }

  function sourceLinks(event) {
    const official = event.official || {};
    const olbg = event.olbg || {};
    return `<div class="source-links">${link(safeUrl(official.url), "Official")}${link(safeUrl(olbg.event), "OLBG")}</div>`;
  }

  function eventRow(event) {
    const r = event.research || {};
    const o = event.olbg || {};
    const flags = (event.flags || []).slice(0, 2);
    const researchLine = r.american === null || r.american === undefined ? "—" : `${american(r.american)}${r.selection ? `<br><span class="xsmall">${esc(r.selection)}</span>` : ""}`;
    return `<tr data-sport="${esc(event.sportKey)}" data-type="${esc(event.eventType)}" data-search="${esc(`${event.event} ${event.sport} ${event.competition || ""} ${o.selection || ""}`.toLowerCase())}">
      <td class="mono">${formatDate(event.startUtc)}<br><span class="badge gray">${esc(typeLabel(event.eventType))}</span></td>
      <td><strong>${esc(event.sport)}</strong>${event.competition ? `<br><span class="xsmall">${esc(event.competition)}</span>` : ""}</td>
      <td><strong>${event.event ? esc(event.event) : "— <span class=\"xsmall\">event name blank in capture</span>"}</strong>${event.venue ? `<br><span class="xsmall">${esc(event.venue)}</span>` : ""}</td>
      <td>${o.selection ? `<strong>${esc(o.selection)}</strong><br><span class="xsmall">${esc(o.market || "OLBG selection")}</span>` : "—"}<br><span class="xsmall">OLBG ${american(o.american)} · ${percent(o.tipPct)} (${esc(o.tips ?? "—")} tips)</span></td>
      <td>${researchLine}${r.market ? `<br><span class="xsmall">${esc(r.market)}</span>` : ""}</td>
      <td>${r.confidence ? badge(r.confidence) : statusBadge(event)}</td>
      <td>${sourceLinks(event)}${flags.length ? `<div class="xsmall" style="margin-top:6px">${esc(flags[0])}</div>` : ""}</td>
    </tr>`;
  }

  function eventTable(events, options = {}) {
    const rows = events.map(eventRow).join("");
    return `<div class="table-wrap"><table class="event-table"><thead><tr>
      <th>Start · type</th><th>Sport</th><th>Event</th><th>OLBG selection</th><th>Our line</th><th>Status</th><th>Sources / note</th>
    </tr></thead><tbody>${rows || `<tr><td colspan="7"><div class="empty">No rows match this filter.</div></td></tr>`}</tbody></table></div>`;
  }

  function sportCard(sport) {
    const href = `sports/${esc(sport.key)}.html`;
    const count = sport.events || 0;
    return `<a class="sport-card" href="${href}"><h3>${esc(sport.label)}</h3><div class="count">${esc(count)}</div><div class="count-label">OLBG listings captured</div><div class="mini"><span>${esc(sport.matchEvents)} matches</span><span>·</span><span>${esc(sport.researchLines)} lines</span></div></a>`;
  }

  function summaryTable(data) {
    return `<div class="table-wrap"><table><thead><tr><th>Sport</th><th>OLBG listings</th><th>Match events</th><th>Research lines</th><th>Written briefs</th><th>State</th></tr></thead><tbody>${data.sports.map(s => `<tr>
      <td><a href="sports/${esc(s.key)}.html"><strong>${esc(s.label)}</strong></a></td><td>${esc(s.events)}</td><td>${esc(s.matchEvents)}</td><td>${esc(s.researchLines)}</td><td>${esc(s.draftPredictions)}</td><td>${s.events ? (s.researchLines ? `<span class="badge flag">research only</span>` : `<span class="badge gray">listed, unpriced</span>`) : `<span class="badge gray">no OLBG listing</span>`}</td>
    </tr>`).join("")}</tbody></table></div>`;
  }

  function renderHome(data) {
    const s = data.summary;
    const upcoming = [...data.events].sort((a, b) => String(a.startUtc).localeCompare(String(b.startUtc))).slice(0, 12);
    root.innerHTML = `<section class="hero">
      <p class="eyebrow">Executive summary · ${esc(data.asOfLabel)}</p>
      <h1>Every OLBG listing in scope, with the line, selection, and evidence status in one place.</h1>
      <p class="lede">This desk separates discovery from recommendation. An event can be listed by OLBG without having enough official identity, current-form, availability, or market evidence for a responsible written prediction.</p>
      <div class="actions"><a class="button primary" href="picks.html">Open picks &amp; written briefs</a><a class="button" href="matches.html">Browse all matches</a><a class="button" href="flagged.html">Review flagged items</a></div>
      <p class="meta-line">Capture: ${esc(data.captureUtc)} · ${esc(data.timezoneNote)}</p>
    </section>
    ${callout("No actionable selections are published.", data.publication.message, "danger")}
    <section class="kpis">${kpi(s.publishedPicks, "Published picks", "publication gate")}${kpi(s.researchLines, "Research lines", "not bookmaker offers")}${kpi(s.eventConfirmed, "Event-confirmed", "official crosswalk")}${kpi(s.olbgEvents, "OLBG listings", "in-scope snapshot")}</section>
    <section><div class="section-head"><div><h2>What matters today</h2><p>The short version before you open the tables.</p></div></div><div class="grid three">
      <div class="card pad"><h3>1 · Where are the picks?</h3><p class="small">The only recommendation page is <a href="picks.html">Picks</a>. It is intentionally empty until a row clears every gate. Four full prose briefs are retained there as withheld research notes.</p></div>
      <div class="card pad"><h3>2 · What is priced?</h3><p class="small">${esc(s.researchLines)} rows have a research line from captured official inputs. They sit beside OLBG’s displayed price and are never represented as an offered market.</p></div>
      <div class="card pad"><h3>3 · What needs review?</h3><p class="small">Most rows are discovery listings only. <a href="flagged.html">Flagged for Review</a> records missing crosswalks, injuries, lineups, market checks, and scope notes.</p></div>
    </div></section>
    <section><div class="section-head"><div><h2>Coverage by sport</h2><p>${esc(s.sportsWithListings)} of ${esc(s.sportsInScope)} requested sports have an OLBG listing in this capture.</p></div><a href="matches.html">Open inventory →</a></div><div class="sport-grid">${data.sports.map(sportCard).join("")}</div></section>
    <section><div class="section-head"><div><h2>Coverage ledger</h2><p>Zeroes are meaningful: they are not filled with another sport’s data.</p></div></div>${summaryTable(data)}</section>
    <section><div class="section-head"><div><h2>Next captured events</h2><p>Sorted by timestamp stored in the capture. Recheck the linked source before use.</p></div><a href="matches.html">See all ${esc(s.olbgEvents)} →</a></div>${eventTable(upcoming)}</section>`;
  }

  function renderMatches(data) {
    root.innerHTML = `${pageHead("Inventory", "All in-scope OLBG listings", "Filter the captured events by sport, event type, team, player, market, or source status. The table makes the selection and the location of every source obvious.")}
      ${callout("Read the status column carefully.", "A research line is a calculated reference price. It is not a live bookmaker price, and a listed selection is not an endorsed pick.", "warn")}
      <div class="filter-bar"><input id="match-search" type="search" placeholder="Search event, sport, selection…" aria-label="Search all listings"><select id="match-sport" aria-label="Filter by sport"><option value="">All sports</option>${data.sports.map(s => `<option value="${esc(s.key)}">${esc(s.label)}</option>`).join("")}</select><select id="match-type" aria-label="Filter by event type"><option value="">All types</option><option value="fixture">Matches</option><option value="race">Races</option><option value="outright">Outrights</option></select><span id="match-count" class="filter-count"></span></div>
      <div id="match-table">${eventTable(data.events)}</div>`;
    const search = document.getElementById("match-search");
    const sport = document.getElementById("match-sport");
    const type = document.getElementById("match-type");
    const count = document.getElementById("match-count");
    const update = () => {
      const q = search.value.trim().toLowerCase();
      const filtered = data.events.filter(e => (!sport.value || e.sportKey === sport.value) && (!type.value || e.eventType === type.value) && (!q || `${e.event} ${e.sport} ${e.olbg?.selection || ""} ${e.olbg?.market || ""}`.toLowerCase().includes(q)));
      count.textContent = `${filtered.length} of ${data.events.length} rows`;
      document.getElementById("match-table").innerHTML = eventTable(filtered);
    };
    [search, sport, type].forEach(el => el.addEventListener("input", update));
    update();
  }

  function renderSport(data) {
    const sport = data.sports.find(s => s.key === sportKey) || data.sports.find(s => s.label.toLowerCase() === sportKey.toLowerCase());
    if (!sport) { root.innerHTML = `<div class="empty">Sport not found. <a href="index.html">Return to overview</a>.</div>`; return; }
    const events = data.events.filter(e => e.sportKey === sport.key);
    root.innerHTML = `${pageHead("Sport desk", sport.label, `${sport.events} OLBG listings captured · ${sport.matchEvents} match events · ${sport.researchLines} research lines · target ${data.dailyTargetPerSport} written picks`)}
      ${callout("Sport-level status", sport.note, sport.events && sport.researchLines ? "warn" : "warn")}
      <div class="detail-grid"><div class="detail"><div class="detail-label">OLBG hub</div><div class="detail-value">${link(sport.olbg_hub, "Open OLBG sport page")}</div></div><div class="detail"><div class="detail-label">Official reference</div><div class="detail-value">${link(sport.official_url, sport.official_name)}</div></div>${sport.official_alt ? `<div class="detail"><div class="detail-label">Additional official reference</div><div class="detail-value">${link(sport.official_alt, sport.official_alt_name)}</div></div>` : ""}<div class="detail"><div class="detail-label">Publication state</div><div class="detail-value">${sport.researchLines ? "Research only; no published pick" : "No line published"}</div></div></div>
      <h2>Listings and lines</h2><p class="small">Every row has an OLBG event link and an official reference. A source status of “reference only” means the official page is a starting point, not an event identity match.</p>${eventTable(events)}`;
  }

  function renderPicks(data) {
    const drafts = data.events.filter(e => e.draftPrediction);
    const published = data.publication.publishedPicks || [];
    root.innerHTML = `${pageHead("Recommendations", "Picks & written predictions", "This page is the only place where a betting selection would be promoted. It stays explicit when the evidence is not sufficient.")}
      ${callout("Published picks: 0", "No row cleared the identity, current-form, relevant-statistics, availability, price-window, and unique-prose gates together. The daily target is not filled with unsupported favourites.", "danger")}
      <section class="card pad"><h2 style="margin-top:0">Published executive picks</h2>${published.length ? published.map(p => `<p>${esc(p)}</p>`).join("") : `<div class="empty">No actionable predictions are published in this capture.</div>`}</section>
      <h2>Full prose briefs withheld from publication</h2><p class="small">These are written research notes, not recommendations. Each is longer than 30 words and links to the official source record, but a missing availability or market check keeps it off the picks list.</p>
      ${drafts.map(e => { const r = e.research; const d = e.draftPrediction; return `<article class="pick-card"><div class="pick-top"><div><div class="sport">${esc(e.sport)} · ${esc(typeLabel(e.eventType))}</div><h3>${esc(e.event)}</h3><div class="small">${formatDate(e.startUtc)} · ${esc(e.official.name)}</div></div><span class="badge flag">withheld</span></div><div class="selection"><div class="selection-label">Research selection · ${esc(d.confidence)} confidence</div><div class="selection-value">${esc(d.selection)} · ${american(r.american)}</div></div><p class="prediction">${esc(d.text)}</p><div class="source-links">${d.source_ids.map(id => { const registry = data.sourceRegistry?.find(x => x.id === id); return registry ? link(registry.url, registry.name) : ""; }).join("")}${link(e.olbg?.event, "OLBG event")}</div></article>`; }).join("")}
      ${!drafts.length ? `<div class="empty">No written briefs were retained for this capture.</div>` : ""}`;
  }

  function renderFlagged(data) {
    const flaggedRows = data.events.filter(e => e.flags && e.flags.length);
    root.innerHTML = `${pageHead("Review register", "Flagged for Review", "Irregularities are visible and linked rather than silently repaired. These do not block the static site, but they block a published pick.")}
      <div class="kpis">${kpi(data.flags.length, "Desk findings", "cross-cutting issues")}${kpi(flaggedRows.length, "Rows with a flag", "event-level review")}${kpi(data.summary.publishedPicks, "Published picks", "none")}${kpi(data.summary.draftPredictions, "Withheld briefs", "not recommendations")}</div>
      ${data.flags.map(f => `<article class="flag-card ${esc(f.severity)}"><div class="flag-head"><span class="flag-id">${esc(f.id)}</span>${badge(f.severity === "high" ? "High" : f.severity === "medium" ? "Medium" : "Low")}</div><h3>${esc(f.title)}</h3><p>${esc(f.body)}</p><div class="source-links">${(f.links || []).map(l => link(l.url, l.label)).join("")}</div></article>`).join("")}
      <h2>Event-level flags</h2><div class="filter-bar"><input id="flag-search" type="search" placeholder="Search flagged rows…" aria-label="Search flagged rows"><span id="flag-count" class="filter-count"></span></div><div id="flag-table"></div>`;
    const input = document.getElementById("flag-search");
    const count = document.getElementById("flag-count");
    const draw = () => {
      const q = input.value.trim().toLowerCase();
      const rows = flaggedRows.filter(e => !q || `${e.event} ${e.sport} ${(e.flags || []).join(" ")}`.toLowerCase().includes(q));
      count.textContent = `${rows.length} of ${flaggedRows.length} flagged rows`;
      document.getElementById("flag-table").innerHTML = `<div class="table-wrap"><table><thead><tr><th>Sport</th><th>Event</th><th>Reason</th><th>Sources</th></tr></thead><tbody>${rows.map(e => `<tr><td><strong>${esc(e.sport)}</strong></td><td><strong>${esc(e.event)}</strong><br><span class="xsmall">${formatDate(e.startUtc)}</span></td><td>${(e.flags || []).map(f => `<div class="xsmall" style="margin-bottom:5px">${esc(f)}</div>`).join("")}</td><td>${sourceLinks(e)}</td></tr>`).join("") || `<tr><td colspan="4"><div class="empty">No flagged row matches this search.</div></td></tr>`}</tbody></table></div>`;
    };
    input.addEventListener("input", draw); draw();
  }

  function renderSources(data) {
    root.innerHTML = `${pageHead("Evidence map", "Sources", "Every inventory row carries two paths: the OLBG discovery page and an official sport or governing-body reference. Event-specific confirmation is labeled in the tables.")}
      ${callout("Source hierarchy", "OLBG establishes what was listed and what selection was displayed. An official governing-body, league, tour, or league API page is required before an event identity or fact is treated as publishable.", "good")}
      <h2>Source register</h2><div class="table-wrap"><table><thead><tr><th>Source</th><th>Kind</th><th>Captured</th><th>What it supports</th><th>Limitation</th></tr></thead><tbody>${(data.sourceRegistry || []).map(s => `<tr><td>${link(s.url, s.name)}</td><td>${esc(s.kind)}</td><td class="mono">${esc(s.captured)}</td><td>${esc(s.supports)}</td><td>${esc(s.limitation)}</td></tr>`).join("")}</tbody></table></div>
      <h2>Official reference by sport</h2><div class="table-wrap"><table><thead><tr><th>Sport</th><th>OLBG hub</th><th>Official reference</th><th>Additional official source</th><th>Rows</th></tr></thead><tbody>${data.sports.map(s => `<tr><td><strong>${esc(s.label)}</strong></td><td>${link(s.olbg_hub, "OLBG")}</td><td>${link(s.official_url, s.official_name)}</td><td>${s.official_alt ? link(s.official_alt, s.official_alt_name) : "—"}</td><td>${esc(s.events)}</td></tr>`).join("")}</tbody></table></div>`;
  }

  function renderMethodology(data) {
    root.innerHTML = `${pageHead("How this desk works", "Methodology & markets", "A reproducible boundary between OLBG discovery, official-source checking, our own reference lines, and publishable written analysis.")}
      <div class="grid two"><section class="card pad"><h2 style="margin-top:0">1. Discover</h2><p class="small">Each in-scope OLBG sport hub follows the observed URL pattern <code>/betting-tips/&lt;Sport&gt;/&lt;sport_id&gt;</code>. The capture records only named events rendered by OLBG. Untipped fixtures can be absent, and “Load More Tips” is a meaningful limitation.</p><p class="small">Football, horse racing, specials, American football, boxing/UFC/MMA, cycling, and hurling are excluded from the dashboard scope.</p></section><section class="card pad"><h2 style="margin-top:0">2. Crosswalk</h2><p class="small">The event name and timing must be matched to a named fixture, race, draw, or tournament on an official league, tour, federation, or governing-body page. A generic official page is retained for every row, but it is labeled “reference only” when it does not establish the exact event.</p></section></div>
      <section class="card pad" style="margin-top:15px"><h2 style="margin-top:0">3. Markets we track</h2><dl class="definition-list"><dt>Match winner / moneyline</dt><dd>Which side wins; in ice hockey and baseball settlement rules can include overtime or extra innings, so the book’s terms still need checking.</dd><dt>Handicap / spread</dt><dd>A margin is applied to the side before settlement. The OLBG event market and the research line are shown separately.</dd><dt>Totals</dt><dd>Over or under a stated combined total. The source must state the line; no total is filled from a guess.</dd><dt>Set / frame / leg</dt><dd>Sport-specific derivative markets such as volleyball set score, snooker frames, or darts legs; a match-winner note is not substituted for these.</dd><dt>Outright / top finish</dt><dd>A tournament or race market, not a daily match. It remains visible but is excluded from the match-pick quota.</dd></dl></section>
      <section class="card pad" style="margin-top:15px"><h2 style="margin-top:0">4. Originate a reference price</h2><p class="small">A line is calculated only for a research row where form and scoring inputs were captured from an official source. It is a fair-price reference, not a live offer and not a claim about bookmaker pricing.</p><div class="formula">For a probability p: if p ≥ 0.50, American price = −100 × p ÷ (1 − p). If p &lt; 0.50, American price = 100 × (1 − p) ÷ p.\n\nInput families captured here: recent team record, scoring for/against, sport-specific margin or total spread, and the event’s official identity status. Missing inputs produce a blank line.</div><p class="small" style="margin-bottom:0">The requested target window is −250 through +10,000. A line outside that window is labeled, not silently clipped.</p></section>
      <section class="card pad" style="margin-top:15px"><h2 style="margin-top:0">5. Confidence and written gate</h2><p class="small">High is at least 70%, Medium is 60–69%, and Low is below 60% based on the research probability. A published written prediction additionally needs an exact event crosswalk, relevant official form and statistics, an availability/injury check where material, a current market check, a line inside the requested range, and unique prose of at least 30 words.</p><p class="small" style="margin-bottom:0">The current capture publishes zero selections. The four prose briefs on the Picks page are deliberately marked <strong>withheld</strong> because at least one gate remains open.</p></section>
      <h2>Capture summary</h2><div class="table-wrap"><table><thead><tr><th>Measure</th><th>Value</th><th>Interpretation</th></tr></thead><tbody><tr><td>Capture time</td><td class="mono">${esc(data.captureUtc)}</td><td>Snapshot time for this static site.</td></tr><tr><td>In-scope OLBG events</td><td>${esc(data.summary.olbgEvents)}</td><td>Named events after removing the explicitly excluded Hurling listing.</td></tr><tr><td>Official event crosswalks</td><td>${esc(data.summary.eventConfirmed)}</td><td>Exact fixture identity located in the captured official sources.</td></tr><tr><td>Research lines</td><td>${esc(data.summary.researchLines)}</td><td>Calculated reference lines; not bookmaker offers.</td></tr><tr><td>Published picks</td><td>0</td><td>Nothing cleared every publication gate.</td></tr></tbody></table></div>`;
  }

  async function start() {
    renderHeader();
    try {
      const response = await fetch(DATA_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`data request returned ${response.status}`);
      const data = await response.json();
      // Keep the source registry in the main payload so pages remain a single fetch.
      const sourceResponse = await fetch(`${BASE}data/sources.json`, { cache: "no-store" });
      if (sourceResponse.ok) {
        const sources = await sourceResponse.json();
        data.sourceRegistry = sources.registry || [];
      } else data.sourceRegistry = [];
      renderFooter(data);
      if (page === "home") renderHome(data);
      else if (page === "matches") renderMatches(data);
      else if (page === "sport") renderSport(data);
      else if (page === "picks") renderPicks(data);
      else if (page === "flagged") renderFlagged(data);
      else if (page === "sources") renderSources(data);
      else if (page === "methodology") renderMethodology(data);
      else renderHome(data);
    } catch (error) {
      if (root) root.innerHTML = `<div class="callout danger"><span class="icon">!</span><p><strong>Dashboard data could not be loaded.</strong> ${esc(error.message)}. Serve the repository root over HTTP for the static JSON files, then reload.</p></div>`;
      console.error(error);
    }
  }

  start();
})();
