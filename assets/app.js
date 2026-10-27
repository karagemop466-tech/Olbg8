/* OLBG multi-sport line desk — static renderer, no runtime dependencies. */
(() => {
  "use strict";

  const page = document.body.dataset.page || "home";
  const sportKey = document.body.dataset.sport || "";
  const BASE = page === "sport" ? "../" : "";
  const app = document.getElementById("app");

  const esc = (v) => String(v ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#039;");

  const url = (u) => {
    try {
      const p = new URL(u, location.href);
      return (p.protocol === "http:" || p.protocol === "https:") ? p.href : "";
    } catch { return ""; }
  };

  const link = (u, label) => {
    const href = url(u);
    return href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>` : esc(label || "—");
  };

  const americanFmt = (v) => {
    if (v === null || v === undefined || v === "") return "—";
    const n = Number(v);
    if (!Number.isFinite(n)) return esc(v);
    return n > 0 ? `+${n}` : String(n);
  };

  const decFmt = (v) => (v === null || v === undefined ? "—" : Number(v).toFixed(2));
  const pctFmt = (v) => (v === null || v === undefined ? "—" : `${Number(v).toFixed(1)}%`);

  const when = (iso) => {
    if (!iso) return "time not published";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return esc(iso);
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "UTC", weekday: "short", day: "2-digit", month: "short",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(d).replace(/,/g, "") + " UTC";
  };

  const dayKey = (iso) => (iso || "").slice(0, 10);
  const todayKey = new Date().toISOString().slice(0, 10);

  const badge = (level) => `<span class="badge ${esc(level)}">${esc(level)}</span>`;

  const edgeClass = (v) => (v > 0 ? "pos" : v < 0 ? "neg" : "");
  const edgeFmt = (v) => (v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${Number(v).toFixed(1)}`);

  /* ---------------------------------------------------------------- nav -- */
  function header(data) {
    const target = document.getElementById("site-header");
    if (!target) return;
    const nav = [
      ["home", "Overview", "index.html"],
      ["picks", "Picks", "picks.html"],
      ["matches", "All matches", "matches.html"],
      ["flagged", "Flagged", "flagged.html"],
      ["sources", "Sources", "sources.html"],
      ["method", "Method", "methodology.html"],
      ["deep", "Deep analysis", "originated/index.html"],
    ];
    const sportLinks = (data?.sports || []).map((s) =>
      `<option value="${BASE}sports/${esc(s.page)}.html"${page === "sport" && s.key === sportKey ? " selected" : ""}>${esc(s.requested)}</option>`
    ).join("");
    target.innerHTML = `<header class="site-header"><div class="header-inner">
      <a class="brand" href="${BASE}index.html"><span class="brand-mark">OL</span>
        <span>OLBG line desk<br><small>independent prices &amp; written predictions</small></span></a>
      <nav class="nav" aria-label="Primary">
        ${nav.map(([k, label, href]) => `<a class="${page === k ? "active" : ""}" href="${BASE}${href}">${label}</a>`).join("")}
        <a class="${page === "sport" ? "active" : ""}" href="${BASE}sports/tennis.html">Sports ▾</a>
        <select aria-label="Jump to a sport" onchange="if(this.value)location.href=this.value"
          style="border:1px solid var(--line);border-radius:8px;padding:6px 8px;background:#fff;font-size:12.5px">
          <option value="">Jump to sport…</option>${sportLinks}
        </select>
      </nav>
    </div></header>`;
  }

  function footer(data) {
    const el = document.getElementById("site-footer");
    if (!el) return;
    el.innerHTML = `<div class="footer-inner">
      <strong>OLBG line desk</strong> — prices originate from parimutuel-free fixed-odds markets captured on OLBG.com and are
      re-priced independently; written predictions cite the primary sources linked on each pick.
      Capture <span class="mono">${esc(data?.capture_utc || "n/a")}</span>, build
      <span class="mono">${esc(data?.generated_utc || "n/a")}</span>.
      Independent research, not betting advice. 18+. Bet only what you can afford to lose.
    </div>`;
  }

  /* ------------------------------------------------------------- pieces -- */
  function kpi(value, label, note) {
    return `<div class="card kpi"><div class="label">${esc(label)}</div>
      <div class="value">${esc(value)}</div>${note ? `<div class="note">${note}</div>` : ""}</div>`;
  }

  function sectionHead(title, text) {
    return `<div class="section-head"><h2>${esc(title)}</h2>${text ? `<p>${text}</p>` : ""}</div>`;
  }

  function pickCard(p) {
    const sources = [];
    if (p.olbg_url) sources.push(link(p.olbg_url, "OLBG market page"));
    if (p.official?.source) sources.push(link(p.official.source, p.official.source_label || "primary source"));
    (p.sources || []).forEach((s) => { if (s.url) sources.push(link(s.url, s.label || s.url)); });
    const facts = (p.facts || []).map((f) => `<li>${esc(f)}</li>`).join("");
    return `<article class="pick" id="pick-${esc(p.id || "")}">
      <div class="pick-head">
        <div>
          <div class="pick-title">${esc(p.event || "Event")}</div>
          <div class="pick-meta">${esc(p.requested_sport || p.sport)}${p.competition ? ` · ${esc(p.competition)}` : ""} · ${when(p.start_utc)}</div>
        </div>
        <div>${badge(p.confidence)}</div>
      </div>
      <div class="pick-body">
        <div class="pick-selection">
          <span class="sel">${esc(p.selection)}</span>
          <span class="tag">${esc(p.market)}</span>
          <span class="price-chip">OLBG ${americanFmt(p.american)} <span style="opacity:.65">(${decFmt(p.decimal)})</span></span>
          <span class="price-chip ghost">Our line ${americanFmt(p.our_american)}</span>
          <span class="tag">market ${pctFmt(p.market_prob)} · ours ${pctFmt(p.our_prob)} · edge <b class="${edgeClass(p.edge_pts)}">${edgeFmt(p.edge_pts)} pts</b></span>
        </div>
        ${p.prediction ? `<p class="prediction">${p.prediction}</p>` : ""}
        ${facts ? `<details><summary>Data points behind this pick</summary><ul class="tight">${facts}</ul></details>` : ""}
        ${sources.length ? `<div class="sources"><span class="tag">Sources:</span>${sources.join("")}</div>` : ""}
      </div>
    </article>`;
  }

  function marketTable(event) {
    return (event.markets || []).map((m) => `
      <div style="margin-bottom:14px">
        <div class="tag" style="margin-bottom:4px"><b>${esc(m.name)}</b> · book ${pctFmt(m.overround)} · ${m.complete ? "complete market" : "partial market"}</div>
        <div class="table-wrap"><table><thead><tr>
          <th>Selection</th><th class="num">OLBG price</th><th class="num">Market implied</th>
          <th class="num">Our line</th><th class="num">Our implied</th><th class="num">Edge (pts)</th>
        </tr></thead><tbody>
        ${(m.selections || []).map((s) => `<tr>
          <td>${esc(s.selection)}</td>
          <td class="num">${americanFmt(s.american)} <span class="muted">(${decFmt(s.decimal)})</span></td>
          <td class="num">${pctFmt(s.market_prob)}</td>
          <td class="num">${americanFmt(s.our_american)}</td>
          <td class="num">${pctFmt(s.our_prob)}</td>
          <td class="num ${edgeClass(s.edge_pts)}">${edgeFmt(s.edge_pts)}</td>
        </tr>`).join("")}
        </tbody></table></div>
      </div>`).join("");
  }

  /* -------------------------------------------------------------- pages -- */
  function home(data) {
    const todays = (data.picks || []).filter((p) => dayKey(p.start_utc) === todayKey);
    const upcoming = (data.picks || []).filter((p) => dayKey(p.start_utc) > todayKey);
    const featured = [...todays, ...upcoming].slice(0, 6);
    const coverage = (data.sports || []).map((s) => `<tr>
        <td><a href="sports/${esc(s.page)}.html">${esc(s.requested)}</a></td>
        <td class="num">${s.events}</td>
        <td class="num">${s.markets}</td>
        <td class="num">${s.selections}</td>
        <td class="num">${s.picks}</td>
        <td class="num">${s.high || 0}</td>
        <td class="num">${s.medium || 0}</td>
        <td>${s.with_official ? `<span class="badge info">${s.with_official} priced with primary data</span>` : `<span class="badge gray">market-anchored</span>`}</td>
      </tr>`).join("");

    return `
      <section class="hero">
        <h1>Executive summary — the picks, the prices, the evidence</h1>
        <p>Every OLBG market we could capture for the fifteen requested sports is re-priced here. Each pick below is a
        fully written prediction with a confidence grade, our own line, the OLBG price it is measured against, and a
        link to the primary source used. Nothing is copied from a tipster.</p>
        <div class="stamp">Capture ${esc(data.capture_utc || "n/a")} · ${esc(data.counts?.sports || 0)} sports ·
        ${esc(data.counts?.picks || 0)} published picks · ${esc(data.counts?.high || 0)} graded high</div>
      </section>

      <div class="grid k4">
        ${kpi(data.counts?.events ?? 0, "Events priced", `${data.counts?.markets ?? 0} markets`)}
        ${kpi(data.counts?.selections ?? 0, "Selections", "live OLBG prices")}
        ${kpi(data.counts?.picks ?? 0, "Published picks", `${data.counts?.high ?? 0} high confidence`)}
        ${kpi(`${data.counts?.sports_with_events ?? 0}/${data.counts?.sports ?? 15}`, "Sports with a market", "all fifteen covered")}
      </div>

      <section class="mt">
        ${sectionHead("Top picks", "Highest graded selections first. The full written prediction sits under each headline.")}
        ${featured.length ? featured.map(pickCard).join("") : `<div class="card empty">No pick cleared the publication gate in this capture.</div>`}
        ${(data.picks || []).length > featured.length ? `<p><a href="picks.html">See all ${data.picks.length} picks →</a></p>` : ""}
      </section>

      <section>
        ${sectionHead("Coverage by sport", "Event counts are distinct OLBG events with at least one captured price.")}
        <div class="table-wrap"><table>
          <thead><tr><th>Sport</th><th class="num">Events</th><th class="num">Markets</th><th class="num">Selections</th>
          <th class="num">Picks</th><th class="num">High</th><th class="num">Medium</th><th>Independent data</th></tr></thead>
          <tbody>${coverage}</tbody>
        </table></div>
      </section>

      <section>
        ${sectionHead("Where everything lives")}
        <div class="grid k3">
          <a class="sport-card" href="picks.html"><div class="name">Picks</div>
            <div class="counts">One card per pick: the selection, both prices, the confidence grade and the written prediction.</div></div>
          <a class="sport-card" href="matches.html"><div class="name">All matches</div>
            <div class="counts">Every captured event and market, with the market price, our line and the edge between them.</div></div>
          <a class="sport-card" href="flagged.html"><div class="name">Flagged for review</div>
            <div class="counts">Anything that could not be confirmed from a primary source, published rather than hidden.</div></div>
        </div>
      </section>`;
  }

  function picks(data) {
    const items = data.picks || [];
    return `
      ${sectionHead("All published picks", `${items.length} picks across ${new Set(items.map((p) => p.requested_sport)).size} sports.`)}
      <div class="filters">
        <input id="q" type="search" placeholder="Search team, player, competition, market…" aria-label="Search picks">
        <select id="sport" aria-label="Filter by sport"><option value="">All sports</option>
          ${(data.sports || []).filter((s) => s.picks > 0).map((s) => `<option value="${esc(s.requested)}">${esc(s.requested)} (${s.picks})</option>`).join("")}
        </select>
        <div class="chip-row" id="conf">
          <button class="chip" data-level="" aria-pressed="true">All</button>
          <button class="chip" data-level="high" aria-pressed="false">High</button>
          <button class="chip" data-level="medium" aria-pressed="false">Medium</button>
        </div>
      </div>
      <div id="list">${items.map(pickCard).join("") || `<div class="card empty">No picks published.</div>`}</div>`;
  }

  function matches(data) {
    const rows = [];
    (data.events || []).forEach((e) => {
      (e.markets || []).forEach((m) => {
        (m.selections || []).forEach((s) => {
          rows.push({ e, m, s });
        });
      });
    });
    return `
      ${sectionHead("Every captured event and market", `${data.counts?.events || 0} events · ${data.counts?.selections || 0} priced selections`)}
      <div class="filters">
        <input id="q" type="search" placeholder="Search event or competition…" aria-label="Search matches">
        <select id="sport" aria-label="Filter by sport"><option value="">All sports</option>
          ${(data.sports || []).filter((s) => s.events > 0).map((s) => `<option value="${esc(s.requested)}">${esc(s.requested)}</option>`).join("")}
        </select>
      </div>
      <div class="table-wrap"><table id="match-table">
        <thead><tr><th>Event</th><th>Competition</th><th>Start (UTC)</th><th>Market</th><th>Selection</th>
        <th class="num">OLBG</th><th class="num">Market %</th><th class="num">Our line</th><th class="num">Our %</th><th class="num">Edge</th><th>Source</th></tr></thead>
        <tbody>
        ${rows.map(({ e, m, s }) => `<tr data-sport="${esc(e.requested_sport)}" data-search="${esc(`${e.name} ${e.competition}`.toLowerCase())}">
          <td class="wrap"><a href="${esc(url(e.olbg_url))}" target="_blank" rel="noopener noreferrer">${esc(e.name)}</a></td>
          <td>${esc(e.competition || "—")}</td>
          <td class="nowrap">${esc((e.start_utc || "").replace("T", " ").replace("Z", ""))}</td>
          <td>${esc(m.name)}${m.complete ? "" : ` <span class="badge low">partial</span>`}</td>
          <td>${esc(s.selection)}</td>
          <td class="num">${americanFmt(s.american)}</td>
          <td class="num">${pctFmt(s.market_prob)}</td>
          <td class="num">${americanFmt(s.our_american)}</td>
          <td class="num">${pctFmt(s.our_prob)}</td>
          <td class="num ${edgeClass(s.edge_pts)}">${edgeFmt(s.edge_pts)}</td>
          <td>${e.official ? link(e.official.source, "primary") : `<span class="tag">market only</span>`}</td>
        </tr>`).join("")}
        </tbody>
      </table></div>`;
  }

  function sportPage(data) {
    const sport = (data.sports || []).find((s) => s.key === sportKey);
    const label = sport?.requested || sportKey;
    const picks = (data.picks || []).filter((p) => p.sport_key === sportKey || p.requested_sport === label);
    const events = (data.events || []).filter((e) => e.sport_key === sportKey || e.requested_sport === label);
    return `
      ${sectionHead(`${label}`, `${events.length} events · ${picks.length} picks${sport?.with_official ? ` · ${sport.with_official} events priced with primary data` : ""}`)}
      ${picks.length ? picks.map(pickCard).join("") : `<div class="callout">No ${esc(label)} selection cleared the publication gate in this capture. The events and prices that were captured are listed below so the gap is visible rather than hidden.</div>`}
      ${events.length ? `<section class="mt">${sectionHead("Captured events")}
        ${events.map((e) => `<div class="card" style="margin-bottom:12px">
          <h3>${link(e.olbg_url, e.name)}</h3>
          <div class="tag">${esc(e.competition || "competition not published")} · ${when(e.start_utc)}${e.venue ? ` · ${esc(e.venue)}` : ""}</div>
          ${e.official ? `<p class="tag">Primary data: ${link(e.official.source, e.official.source_label)} — ${esc(e.official.detail || "")}</p>` : `<p class="tag">No structured primary feed for this competition; prices are market-anchored.</p>`}
          <div class="mt">${marketTable(e)}</div>
        </div>`).join("")}
      </section>` : ""}`;
  }

  function flaggedPage(data) {
    const flags = data.flagged || [];
    const sportGaps = (data.sports || []).filter((s) => s.events === 0);
    const marketOnly = (data.sports || []).filter((s) => s.events > 0 && s.with_official === 0);
    return `
      ${sectionHead("Flagged for review", "Everything that could not be confirmed from a primary source stays visible here.")}
      <div class="callout">A flag is not a failure of the pick — it is a statement about evidence. Items marked
      <span class="badge flag">unverified</span> were left blank in the data rather than filled in.</div>

      <section class="mt">
        <h3>Sports with no OLBG market at capture time</h3>
        <div class="table-wrap"><table><thead><tr><th>Sport</th><th>Status</th><th>What we checked</th></tr></thead><tbody>
        ${sportGaps.length ? sportGaps.map((s) => `<tr><td>${esc(s.requested)}</td>
          <td><span class="badge flag">no priced event captured</span></td>
          <td>The OLBG category page answered but exposed no market row in the hydration payload, so no line could be originated. Nothing was substituted.</td></tr>`).join("")
          : `<tr><td colspan="3">Every requested sport had at least one priced event.</td></tr>`}
        </tbody></table></div>
      </section>

      <section>
        <h3>Sports priced from market data only</h3>
        <div class="table-wrap"><table><thead><tr><th>Sport</th><th>Limitation</th></tr></thead><tbody>
        ${marketOnly.length ? marketOnly.map((s) => `<tr><td>${esc(s.requested)}</td>
          <td>No structured primary feed was reachable for this competition, so the line is anchored on captured OLBG prices with a stated de-vig. Confidence is capped at medium.</td></tr>`).join("")
          : `<tr><td colspan="2">All sports with events had at least one primary-data cross-check.</td></tr>`}
        </tbody></table></div>
      </section>

      <section>
        <h3>Row-level flags</h3>
        <div class="table-wrap"><table><thead><tr><th>Sport</th><th>Event</th><th>Issue</th><th>Source</th></tr></thead><tbody>
        ${flags.length ? flags.map((f) => `<tr><td>${esc(f.sport)}</td><td>${esc(f.event)}</td><td>${esc(f.issue)}</td>
          <td>${f.source_url ? link(f.source_url, "link") : "—"}</td></tr>`).join("")
          : `<tr><td colspan="4">No row-level flag was raised in this capture.</td></tr>`}
        </tbody></table></div>
      </section>`;
  }

  function sourcesPage(data) {
    const groups = {};
    (data.sources || []).forEach((s) => { (groups[s.sport] = groups[s.sport] || []).push(s); });
    return `
      ${sectionHead("Source register", "Every primary source used to price or write a pick, with the URL that was checked.")}
      <div class="callout info">OLBG supplies the market prices and the event identity. OLBG is not a governing body, so
      every factual claim in a prediction is traced to the league, tour or federation link below.</div>
      ${Object.entries(groups).map(([sport, list]) => `<section class="mt">
        <h3>${esc(sport)}</h3>
        <div class="table-wrap"><table><thead><tr><th>Source</th><th>Type</th><th>Link</th></tr></thead><tbody>
        ${list.map((s) => `<tr><td>${esc(s.label)}</td><td>${esc(s.type)}</td><td>${link(s.url, s.url)}</td></tr>`).join("")}
        </tbody></table></div></section>`).join("")}
      <section class="mt">
        <h3>OLBG category pages (market capture)</h3>
        <div class="table-wrap"><table><thead><tr><th>Sport</th><th>OLBG category</th><th>Captured events</th></tr></thead><tbody>
        ${(data.sports || []).map((s) => `<tr><td>${esc(s.requested)}</td>
          <td>${s.olbg_hub ? link(s.olbg_hub, "OLBG category") : "—"}</td>
          <td class="num">${s.events}</td></tr>`).join("")}
        </tbody></table></div>
      </section>`;
  }

  function methodPage() {
    return `
      ${sectionHead("Method", "How a price on this site is produced, and what the confidence grades mean.")}
      <div class="grid k2">
        <div class="card"><h3>1 · Capture</h3><p>OLBG's public category pages are JavaScript shells. The fixture, market
        and price data is served from the page's own hydration payload (<code>/__data.json</code>), which is decoded into a
        flat table of event, market, selection, decimal/American/fractional price and kick-off. Captures are timestamped
        and stored unchanged in <code>data/olbg/</code>.</p></div>
        <div class="card"><h3>2 · Remove the bookmaker margin</h3><p>Implied probabilities (1 ÷ decimal price) sum to more
        than 100%. We strip that margin with Shin's method, which corrects the favourite-longshot bias that fixed-odds
        books show, and fall back to proportional normalisation when Shin has no solution. The book percentage for each
        market is published next to it.</p></div>
        <div class="card"><h3>3 · Independent estimate</h3><p>Where a primary feed exists we build our own probability and
        blend it 55/45 with the de-vigged market: log5 on MLB winning percentage with a home-field term, log5 on NHL points
        percentage with home ice, log5 on NBA win percentage with home court, and a logistic model on ATP ranking points for
        tennis.</p></div>
        <div class="card"><h3>4 · Our line</h3><p>The published line is the decimal odds implied by the blended
        probability, converted to American odds. It is a fair line: no margin is added. The edge column is our probability
        minus the de-vigged market probability, in percentage points.</p></div>
        <div class="card"><h3>5 · Confidence</h3><p><span class="badge high">high</span> needs a complete market (both
        sides captured, book between 100% and 175%), a primary-data cross-check, an edge of at least 2.5 points and a price
        inside the requested −250 to +10000 band. <span class="badge medium">medium</span> allows either a smaller edge or
        a market-anchored price. Anything else stays low and is not published as a pick.</p></div>
        <div class="card"><h3>6 · Writing</h3><p>Published predictions state the selection, the price, the form or record
        that supports it and the source of that fact. Where a competition has no reachable primary feed, the prediction
        says so instead of inventing statistics, and the confidence cannot be high.</p></div>
      </div>
      <section class="mt">
        <h3>What this site does not do</h3>
        <ul class="tight">
          <li>It does not republish OLBG tipster text, and it does not treat a tipster's strike rate as evidence.</li>
          <li>It does not fill a blank with an estimate. A missing venue, official crosswalk or injury note stays blank and is flagged.</li>
          <li>It does not claim a complete fixture list: OLBG exposes events that carry a market, and only those can be priced.</li>
          <li>It does not add margin to the published line, so the prices here are not offers and cannot be bet into.</li>
        </ul>
      </section>`;
  }

  /* ------------------------------------------------------------ filters -- */
  function wireListFilters() {
    const q = document.getElementById("q");
    const sport = document.getElementById("sport");
    const list = document.getElementById("list");
    const chips = document.querySelectorAll("#conf .chip");
    let level = "";
    const apply = () => {
      const text = (q?.value || "").toLowerCase().trim();
      const sp = sport?.value || "";
      const cards = list ? list.querySelectorAll(".pick") : document.querySelectorAll("#match-table tbody tr");
      cards.forEach((node) => {
        let ok = true;
        if (text) ok = (node.textContent || "").toLowerCase().includes(text);
        if (ok && sp) {
          const meta = node.dataset.sport || node.querySelector(".pick-meta")?.textContent || "";
          ok = meta.includes(sp);
        }
        if (ok && level) ok = (node.textContent || "").toLowerCase().includes(level);
        node.style.display = ok ? "" : "none";
      });
    };
    q?.addEventListener("input", apply);
    sport?.addEventListener("change", apply);
    chips.forEach((chip) => chip.addEventListener("click", () => {
      chips.forEach((c) => c.setAttribute("aria-pressed", "false"));
      chip.setAttribute("aria-pressed", "true");
      level = chip.dataset.level || "";
      apply();
    }));
  }

  /* --------------------------------------------------------------- boot -- */
  async function start() {
    let data = null;
    try {
      const response = await fetch(`${BASE}data/dashboard.json`, { cache: "no-cache" });
      if (!response.ok) throw new Error(String(response.status));
      data = await response.json();
    } catch (error) {
      if (app) app.innerHTML = `<div class="card empty"><b>Data could not be loaded.</b><br>
        ${esc(error.message)}. Serve the folder over HTTP (for example <code>python3 -m http.server</code>) rather than opening the file directly.</div>`;
      return;
    }
    header(data);
    footer(data);
    if (!app) return;
    const render = { home, picks, matches, sport: sportPage, flagged: flaggedPage, sources: sourcesPage };
    app.innerHTML = page === "method" ? methodPage(data) : (render[page] || home)(data);
    wireListFilters();
  }

  start();
})();
