(() => {
  const body = document.body;
  const prefix = body.dataset.dataPrefix || '';
  const page = body.dataset.page || 'home';
  const currentSport = body.dataset.sport || '';
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const sourceLink = (label, url, cls = '') => `<a class="${cls}" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} <span aria-hidden="true">↗</span></a>`;

  async function loadData() {
    const [sportsResponse, eventsResponse] = await Promise.all([
      fetch(`${prefix}data/sports.json`), fetch(`${prefix}data/events.json`)
    ]);
    if (!sportsResponse.ok || !eventsResponse.ok) throw new Error('Dashboard data could not be loaded.');
    return {sports: await sportsResponse.json(), snapshot: await eventsResponse.json()};
  }

  function renderNav() {
    const nav = document.getElementById('site-nav');
    if (!nav) return;
    const homeHref = page === 'home' ? 'index.html' : '../index.html';
    const flagsHref = page === 'home' ? 'flagged-for-review.html' : '../flagged-for-review.html';
    nav.innerHTML = `<a href="${homeHref}" ${page === 'home' ? 'aria-current="page"' : ''}>Dashboard</a><a href="${flagsHref}" ${page === 'flags' ? 'aria-current="page"' : ''}>Flagged for Review</a>`;
  }

  function emptyCell() { return '<span class="empty-value" aria-label="Not confirmed">—</span>'; }

  function renderHome(sports, snapshot) {
    const grid = document.getElementById('sport-grid');
    const counts = Object.fromEntries(sports.map(s => [s.slug, snapshot.events.filter(e => e.sport === s.slug).length]));
    if (grid) grid.innerHTML = sports.map(s => `<a class="sport-card" href="sports/${esc(s.slug)}.html"><span class="sport-card-top"><span class="sport-icon">${esc(s.name.slice(0,1))}</span><span class="arrow" aria-hidden="true">↗</span></span><strong>${esc(s.name)}</strong><span class="sport-card-bottom"><span>${counts[s.slug] ? `${counts[s.slug]} listing ${counts[s.slug] === 1 ? 'sighting' : 'sightings'}` : 'No sighting in snapshot'}</span><span class="card-state">${counts[s.slug] ? 'Unverified' : 'Awaiting data'}</span></span></a>`).join('');
    const snapshotMeta = document.getElementById('snapshot-meta');
    if (snapshotMeta) snapshotMeta.innerHTML = `Snapshot reviewed ${esc(snapshot.snapshotDate)} UTC · ${sourceLink('OLBG source page', snapshot.snapshotSource, 'inline-link')}`;
    const sightings = document.getElementById('metric-sightings');
    if (sightings) sightings.textContent = String(snapshot.events.length);
    const sportCount = document.getElementById('metric-sports');
    if (sportCount) sportCount.textContent = String(sports.length);
  }

  function renderSport(sports, snapshot) {
    const sport = sports.find(item => item.slug === currentSport);
    const root = document.getElementById('sport-content');
    if (!sport || !root) return;
    document.title = `${sport.name} · OLBG Match Research`;
    const events = snapshot.events.filter(e => e.sport === sport.slug);
    const eventRows = events.map(event => `<tr>
      <td><strong>${esc(event.name)}</strong><div class="row-sub">Source sighting only · exact fixture not confirmed</div></td>
      <td>${esc(event.olbgTime)}<div class="row-sub">Relative label, not a confirmed date/time zone</div></td>
      <td><span class="pill pill-review">Pending</span><div class="row-sub">No event-specific primary-source check recorded</div></td>
      <td>${emptyCell()}</td><td>${emptyCell()}</td><td>${emptyCell()}</td><td>${emptyCell()}</td>
      <td>${sourceLink('OLBG event page', event.olbgUrl)}<br>${sourceLink('Sport authority', sport.authorityUrl)}</td>
    </tr>`).join('');
    root.innerHTML = `<section class="sport-intro"><a class="back-link" href="../index.html">← All sports</a><p class="eyebrow">SPORT RESEARCH PAGE</p><h1>${esc(sport.name)}</h1><p class="lead">Event sightings, primary-source checkpoints and pricing status for ${esc(sport.name.toLowerCase())}. Blank means no supporting evidence has been entered; it does not mean zero or unavailable.</p><div class="source-chips">${sourceLink('OLBG sport listings', sport.olbg)}${sourceLink(sport.authority, sport.authorityUrl)}</div><p class="source-note">${esc(sport.note)}</p></section>
      <section class="summary-panel compact-panel"><div class="section-heading"><div><p class="eyebrow">CURRENT STATUS</p><h2>No qualifying picks published</h2></div><span class="pill pill-review">${events.length} listing ${events.length === 1 ? 'sighting' : 'sightings'}</span></div><p>There is no independently confirmed event/market record on this page. We therefore have not originated a line, named a selection, assigned a confidence level, or written a prediction. OLBG tipster consensus is not substituted for odds.</p></section>
      <section class="section-block"><div class="section-heading"><div><p class="eyebrow">EVENT REGISTER</p><h2>${events.length ? 'OLBG snapshot sightings' : 'No event sighting captured'}</h2></div><span class="muted">Snapshot: ${esc(snapshot.snapshotDate)} UTC</span></div>
      ${events.length ? `<div class="table-wrap"><table><thead><tr><th>Event listed by OLBG</th><th>OLBG time label</th><th>Official fixture check</th><th>Selection</th><th>Our line / price</th><th>Confidence</th><th>Written analysis</th><th>Source links</th></tr></thead><tbody>${eventRows}</tbody></table></div>` : `<div class="empty-state"><span class="empty-state-icon">—</span><h3>No captured listing in this snapshot</h3><p>This is not evidence that the sport has no upcoming events. Check the linked OLBG listing and primary-source schedule; no event data has been entered here.</p>${sourceLink('Open OLBG listings', sport.olbg)} ${sourceLink('Open primary schedule source', sport.authorityUrl)}</div>`}
      <p class="fine-print">All event names/time labels above are transcribed from the linked OLBG page on ${esc(snapshot.snapshotDate)}. OLBG uses relative Today/Tomorrow labels. Official fixture, local date, participants, market availability, prices, statistics and injuries remain unconfirmed.</p></section>
      <section class="section-block market-block"><div class="section-heading"><div><p class="eyebrow">MARKET COVERAGE</p><h2>Markets to price when available</h2></div></div><div class="market-tags"><span>Match / event winner</span><span>Handicap / spread</span><span>Total points / runs / frames</span><span>Set / period / segment</span><span>Outright / placement</span><span>Event-specific prop markets</span></div><p class="fine-print">This is a research checklist, not a claim that OLBG or a bookmaker offers each market for every event. Event-specific availability, odds, timestamp and bookmaker are blank until sourced.</p></section>
      <footer class="site-footer"><span>Nothing here is a betting recommendation.</span><a href="../flagged-for-review.html">Review outstanding issues →</a></footer>`;
  }

  function renderFlags(sports, snapshot) {
    const root = document.getElementById('flag-content');
    if (!root) return;
    root.innerHTML = `<section class="sport-intro"><a class="back-link" href="index.html">← Dashboard</a><p class="eyebrow">TRANSPARENCY LOG</p><h1>Flagged for Review</h1><p class="lead">Known gaps and source limitations are surfaced here rather than hidden behind blank cells or fabricated analysis.</p></section>
    <section class="summary-panel compact-panel"><div class="section-heading"><div><p class="eyebrow">AS OF ${esc(snapshot.snapshotDate)} UTC</p><h2>No picks pass the publication gate</h2></div><span class="pill pill-review">${snapshot.events.length} unconfirmed sightings</span></div><p>The landing page snapshot exposed a limited set of OLBG entries. It is not a complete feed, does not verify the fixtures independently and does not establish bookmaker prices. No selection, originated line or 30-word prediction is published as a result.</p></section>
    <section class="section-block"><div class="section-heading"><div><p class="eyebrow">OPEN ISSUES</p><h2>What remains unverified</h2></div></div><div class="flag-list">
      <article class="flag-item"><span class="flag-number">01</span><div><h3>Completeness and freshness</h3><p>The source page is dynamic and offers a limited visible slice. This snapshot is not a full list of today's or upcoming events across OLBG's sport categories. No automated refresh/API integration exists.</p><p>Impact: events may be missing or listings may have changed since capture. Relative “Today/Tomorrow” labels are not converted to local dates.</p>${sourceLink('OLBG betting-tips page', snapshot.snapshotSource)}</div></article>
      <article class="flag-item"><span class="flag-number">02</span><div><h3>Primary fixture confirmation</h3><p>Every captured event sighting still requires an event-specific confirmation from the governing body, league or tournament organizer. The organization links on the sport pages are source starting points only; they are not evidence that the listed fixture was checked or confirmed.</p><p>Impact: event status, start time/time zone, venue and participants remain blank.</p></div></article>
      <article class="flag-item"><span class="flag-number">03</span><div><h3>Odds and originated lines</h3><p>No bookmaker prices, market definitions, timestamped odds, margin adjustments or independent probability calculations were available in the reviewed source. OLBG tip counts and selection percentages are community opinion, not odds.</p><p>Impact: the requested odds range (-250 to +10000), fair prices, match winner picks and alternative markets cannot be assessed.</p>${sourceLink('How OLBG describes tipster consensus', snapshot.snapshotSource)}</div></article>
      <article class="flag-item"><span class="flag-number">04</span><div><h3>Match research and player availability</h3><p>No event-specific official statistics, recent results, rosters, injury reports or lineup confirmations were cross-checked for these sightings.</p><p>Impact: no form, head-to-head, stat or injury claims and no purported high-confidence prediction are published.</p></div></article>
      <article class="flag-item"><span class="flag-number">05</span><div><h3>Unsupported sport coverage</h3><p>The current OLBG landing-page sample produced no event sightings for some tracked categories. That is not evidence there are no upcoming markets. Each category page links to OLBG and a relevant governing body or schedule starting point.</p><p>Impact: sport coverage is not yet a complete upcoming-event register.</p></div></article>
    </div></section>
    <section class="section-block"><div class="section-heading"><div><p class="eyebrow">SOURCE MAP</p><h2>Primary-source starting points</h2></div><span class="muted">Not event-level verification</span></div><div class="table-wrap"><table><thead><tr><th>Sport</th><th>Official organization / schedule starting point</th><th>OLBG listing</th><th>Event-level check</th></tr></thead><tbody>${sports.map(s => `<tr><td><a href="sports/${esc(s.slug)}.html">${esc(s.name)}</a></td><td>${sourceLink(s.authority, s.authorityUrl)}<div class="row-sub">${esc(s.note)}</div></td><td>${sourceLink('OLBG',s.olbg)}</td><td><span class="pill pill-review">Not recorded</span></td></tr>`).join('')}</tbody></table></div><p class="fine-print">Links provide a route to relevant organizations. They should not be read as confirmation that an organization posted or verified any specific fixture, market or statistic for this snapshot.</p></section>
    <footer class="site-footer"><span>Last source review recorded: ${esc(snapshot.snapshotDate)} UTC.</span><a href="index.html">Back to dashboard</a></footer>`;
  }

  renderNav();
  loadData().then(({sports, snapshot}) => {
    if (page === 'home') renderHome(sports, snapshot);
    else if (page === 'sport') renderSport(sports, snapshot);
    else if (page === 'flags') renderFlags(sports, snapshot);
  }).catch(error => {
    const target = document.getElementById(page === 'sport' ? 'sport-content' : page === 'flags' ? 'flag-content' : 'sport-grid');
    if (target) target.innerHTML = `<p class="notice" role="alert">${esc(error.message)} Open the source JSON files in <code>data/</code> or reload the page.</p>`;
  });
})();
