/* Independent research desk. External data is escaped and never interpreted as HTML. */
(() => {
  'use strict';
  const BASE = document.body.dataset.base || '.';
  const page = document.body.dataset.page || 'home';
  const sportKey = document.body.dataset.sport || '';
  const app = document.querySelector('#app');
  const esc = value => String(value ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  const local = path => `${BASE}/${path}`;
  const safe = value => { try { const u = new URL(value); return u.protocol === 'https:' ? u.href : ''; } catch (_) { return ''; } };
  const external = (url, label, title='') => safe(url) ? `<a class="source-link" href="${esc(safe(url))}" target="_blank" rel="noopener noreferrer"${title ? ` title="${esc(title)}"` : ''}>${esc(label)} ↗</a>` : '';
  const icons = {
    grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    list:'<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>',
    file:'<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h4M9 12h6M9 16h6"/>',
    flag:'<path d="M5 21V4m0 0c5-3 8 3 14 0v10c-6 3-9-3-14 0"/>',
    book:'<path d="M3 5a3 3 0 013-3h5v17H6a3 3 0 00-3 3zM21 5a3 3 0 00-3-3h-5v17h5a3 3 0 013 3z"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/>',
    check:'<path d="M12 3l7 3v5c0 4-2.5 7-7 10-4.5-3-7-6-7-10V6z"/><path d="M9 12l2 2 4-4"/>',
    layers:'<path d="M12 3L3 8l9 5 9-5zM3 12l9 5 9-5M3 16l9 5 9-5"/>',
    arrow:'<path d="M5 12h14M14 7l5 5-5 5"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    warning:'<path d="M12 3L2 20h20L12 3zM12 9v4m0 3h.01"/>',
    ball:'<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 4 6 4 9s-1 6-4 9M12 3c-3 3-4 6-4 9s1 6 4 9"/>'
  };
  const icon = (name, size=16) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || icons.ball}</svg>`;
  const humanTime = iso => { const d = new Date(iso || ''); return Number.isFinite(d.getTime()) ? new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'UTC',hourCycle:'h23'}).format(d).replace(',', '') + ' UTC' : 'Time not established'; };
  const shortTime = iso => { const d = new Date(iso || ''); return Number.isFinite(d.getTime()) ? new Intl.DateTimeFormat('en-GB',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',timeZone:'UTC',hourCycle:'h23'}).format(d).replace(',', '') + ' UTC' : '—'; };
  const price = odds => odds && Number.isFinite(Number(odds.american)) ? `${Number(odds.american) > 0 ? '+' : ''}${esc(odds.american)}` : '—';
  const ageText = date => { const delta = Date.now() - new Date(date).getTime(); if (!Number.isFinite(delta) || delta < -300000) return 'time unavailable'; const mins = Math.max(0,Math.floor(delta/60000)); return mins < 2 ? 'just now' : mins < 60 ? `${mins} min ago` : mins < 1440 ? `${Math.floor(mins/60)} hr ago` : `${Math.floor(mins/1440)} days ago`; };
  const stale = date => !date || !Number.isFinite(new Date(date).getTime()) || Date.now() - new Date(date).getTime() > 3*3600000 || new Date(date).getTime() - Date.now() > 300000;
  const displayable = e => { const times = [e.start,e.official?.start].map(x => new Date(x || '').getTime()).filter(Number.isFinite); return !times.length || Math.min(...times) > Date.now(); };
  const difference = e => { const a = new Date(e.start || '').getTime(), b = new Date(e.official?.start || '').getTime(); return Number.isFinite(a) && Number.isFinite(b) ? Math.round((a-b)/60000) : null; };
  const briefState = b => Date.now() >= new Date(b.expiresAt).getTime() ? 'Past event · archived' : Date.now() - new Date(b.checkedAt).getTime() > 24*3600000 ? 'Stale · needs recheck' : 'Needs review';

  function renderChrome(data) {
    const nav = [ ['home','Overview','index.html','grid'], ['listings','All listings','listings.html','list'], ['briefs','Research briefs','briefs.html','file'], ['review','Flagged for review','review.html','flag'], ['method','Methodology','methodology.html','book'] ];
    document.querySelector('#sidebar').innerHTML = `<aside class="sidebar">
      <a class="brand" href="${local('index.html')}"><span class="brand-mark">o.</span><span><span class="brand-title">The Research Desk</span><span class="brand-sub">Independent sports</span></span></a>
      <p class="nav-label">Workspace</p><nav class="side-nav" aria-label="Main navigation">${nav.map(([id,label,url,ic])=>`<a class="nav-link ${page===id?'active':''}" href="${local(url)}" ${page===id?'aria-current="page"':''}>${icon(ic)}${label}</a>`).join('')}</nav>
      <p class="nav-label">Sports coverage</p><nav class="sport-nav" aria-label="Sport categories">${data.sports.map(s=>`<a class="nav-link ${sportKey===s.key?'active':''}" href="${local(`sports/${s.key}.html`)}" ${sportKey===s.key?'aria-current="page"':''}><span class="dot"></span>${esc(s.name)}</a>`).join('')}</nav>
      <label class="mobile-sports"><span class="sr-only">Choose a sport</span><select id="mobile-sport"><option value="">Browse sports…</option>${data.sports.map(s=>`<option value="${esc(s.key)}" ${sportKey===s.key?'selected':''}>${esc(s.name)}</option>`).join('')}</select></label>
      <div class="side-bottom">Source-first, never a live odds service.<br><a href="${local('../snapshot.html')}">View 26 Oct archive ↗</a></div></aside>`;
    const picker = document.querySelector('#mobile-sport');
    picker?.addEventListener('change', e=>{ if (e.target.value) location.href=local(`sports/${encodeURIComponent(e.target.value)}.html`); });
    const errors = data.hubs.filter(h=>h.status==='error').length;
    const fresh = !stale(data.capturedAt) && errors === 0;
    const freshness = stale(data.capturedAt) ? 'Refresh overdue' : errors ? `${errors} source error${errors===1?'':'s'}` : 'Source snapshot';
    document.querySelector('#topbar').innerHTML = `<div class="topbar"><div class="top-left">RESEARCH DESK <span style="padding:0 7px;color:#c9d6cf">/</span> <strong>${esc(page==='sport' ? data.sports.find(s=>s.key===sportKey)?.name || 'Sport' : ({home:'Overview',listings:'All listings',briefs:'Research briefs',review:'Flagged for review',method:'Methodology'}[page] || 'Overview'))}</strong></div><div class="top-right"><span class="live-dot ${fresh?'':'stale'}"></span><span>${fresh?'Captured':'Snapshot'} ${esc(ageText(data.capturedAt))}</span><span class="top-pill ${fresh?'':'warn'}">${esc(freshness)}</span></div></div>`;
    document.querySelector('#footer').innerHTML = `<footer class="footer"><p><strong>The Research Desk</strong> · independent, source-first research<br>Capture: ${esc(humanTime(data.capturedAt))}</p><p>Prices are observations, not offers. Check all sources and limits.<br><a href="https://www.ncpgambling.org/help-treatment/" target="_blank" rel="noopener noreferrer">Gambling support ↗</a></p></footer>`;
  }

  function head(eyebrow, title, text, actions='') {
    return `<div class="breadcrumb">Research desk <span>/</span> ${esc(title)}</div><div class="page-head"><div><p class="eyebrow">${esc(eyebrow)}</p><h1>${esc(title)}</h1><p>${esc(text)}</p></div>${actions?`<div class="head-actions">${actions}</div>`:''}</div>`;
  }
  const action = (label,path,primary=false) => `<a class="button ${primary?'primary':''}" href="${local(path)}">${esc(label)} ${icon('arrow',14)}</a>`;
  const section = (title,sub,more='',href='') => `<div class="section-head"><div><h2>${esc(title)}</h2>${sub?`<p>${esc(sub)}</p>`:''}</div>${href?`<a href="${local(href)}">${esc(more)} →</a>`:''}</div>`;
  const notice = (title,text,info=false) => `<div class="notice ${info?'info':''}">${icon(info?'check':'warning',18)}<div><strong>${esc(title)}</strong> ${text}</div></div>`;
  const stat = (label,value,note,ic) => `<div class="stat"><div class="stat-top"><span>${esc(label)}</span><span class="stat-icon">${icon(ic,16)}</span></div><div class="stat-value">${esc(value)}</div><div class="stat-note">${esc(note)}</div></div>`;

  function marketDetails(row) {
    const detail = row.details;
    if (!detail) return '';
    if (detail.status !== 'ok') return `<span class="status-text">Market detail: ${esc(detail.status)}${detail.detail ? ` (${esc(detail.detail)})` : ''}</span>`;
    if (!detail.markets?.length) return '';
    return `<details class="mini-details"><summary>${detail.markets.length} sampled market${detail.markets.length===1?'':'s'}</summary><div class="market-list">${detail.markets.map(m=>`<div><div class="market-name">${esc(m.name)}</div><div class="market-outcomes">${(m.selections || []).map(s=>`${esc(s.selection)} <strong>${price(s.odds)}</strong>`).join(' · ') || 'No outcomes captured'}</div></div>`).join('')}</div></details>`;
  }
  function sourceStatus(e) {
    if (!e.official) return 'Official event not matched';
    if (e.official.kind === 'manual' && Date.now() - new Date(e.official.checkedAt).getTime() > 24*3600000) return 'Manual source check is stale';
    const d = difference(e);
    if (d !== null && d !== 0) return `Start times differ by ${Math.abs(d)} min`;
    return e.official.kind === 'manual' && !e.official.start ? 'Official identity; time not checked' : 'Official event matched';
  }
  function referenceCell(e) {
    const r = e.researchLine;
    if (r) return `<strong>${esc(r.home)} ${price({american:r.homeAmerican})}</strong><span class="subtle">${esc(r.away)} ${price({american:r.awayAmerican})} · uncalibrated</span><span class="status-text">Reference only, review</span><details class="mini-details"><summary>Inputs &amp; limits</summary><div class="market-list">${[r.home,r.away].map(team=>{const v=r.inputs[team];return `<div>${esc(team)}: ${esc(v.gamesPlayed)} games, ${esc(v.goalFor)} goals for, ${esc(v.goalAgainst)} against</div>`;}).join('')}<div>Equal split of tied scores; no goalie, injury, home-ice or calibration adjustment.</div><div>${external(r.source,'NHL standings')}</div></div></details>`;
    const b=e.referenceBrief;
    if (b) return `<strong>${price(b.researchLine)}</strong><span class="subtle">${esc(b.selection)} · uncalibrated</span><span class="status-text">Reference only, review</span><a class="source-link" href="${local('briefs.html')}">Inputs &amp; limits →</a>`;
    return '—<span class="subtle">No independent line</span>';
  }
  function eventRow(e,sport) {
    const official = e.official?.url || sport.official;
    const specific = !!e.official;
    const mainTime = e.official?.start || e.start;
    const timeLabel = e.official?.start ? 'Official start' : 'OLBG time only';
    const d = difference(e);
    return `<tr>
      <td class="event-name"><strong>${esc(e.event || 'Event name not supplied')}</strong><span class="subtle">${esc(sport.name)}${e.competition ? ` · ${esc(e.competition)}` : ''}${e.hub==='Hurling'?' · Hurling':''}</span>${marketDetails(e)}</td>
      <td class="time"><strong>${esc(shortTime(mainTime))}</strong><span class="subtle">${esc(timeLabel)}</span>${d!==null&&d!==0?`<span class="status-text">OLBG: ${esc(shortTime(e.start))}</span>`:''}</td>
      <td class="selection">${e.selection?`<strong>${esc(e.selection)}</strong><span class="subtle">${esc(e.market || 'Market not supplied')}</span>`:'—<span class="subtle">No selection captured</span>'}</td>
      <td><span class="price">${price(e.odds)}</span><span class="subtle">${e.odds?'OLBG snapshot':'Not supplied'}</span></td>
      <td>${referenceCell(e)}</td>
      <td class="sources">${external(official,specific?'Official event':'Official directory',specific?'Source for the event identity':'General sport reference; not an event match')} ${external(e.url,'OLBG')}<span class="${specific && !(d!==null&&d!==0) ? 'subtle':'status-text'}">${esc(sourceStatus(e))}</span></td>
    </tr>`;
  }
  function table(rows, data, options={}) {
    const sports = Object.fromEntries(data.sports.map(s=>[s.key,s]));
    return `<div class="table-wrap"><table><thead><tr><th>Event / sport</th><th>Start</th><th>OLBG popular selection</th><th>Observed odds</th><th>Our reference</th><th>Sources &amp; status</th></tr></thead><tbody>${rows.map(e=>eventRow(e,sports[e.sport])).join('') || `<tr><td colspan="6" class="empty">${esc(options.empty || 'No upcoming entries match this view.')}</td></tr>`}</tbody></table></div>`;
  }
  function sportCard(s,events,data) {
    const count = events.filter(e=>e.sport===s.key).length;
    const hubs = data.hubs.filter(h=>h.sport===s.key);
    const unavailable = hubs.some(h=>h.status==='error');
    return `<a class="sport-card" href="${local(`sports/${s.key}.html`)}"><div class="sport-card-top"><span class="sport-icon">${icon('ball',16)}</span><span class="sport-arrow">↗</span></div><h3>${esc(s.name)}</h3><p>${unavailable ? `${count} listed · partial` : `${count} upcoming listed`}</p></a>`;
  }
  function briefCard(b) {
    const state = briefState(b);
    const line = b.researchLine;
    return `<article class="brief"><div class="brief-head"><div><p class="eyebrow" style="margin-bottom:6px">${esc(b.sport.replace(/-/g,' '))} · ${esc(b.event)}</p><h3>${esc(b.selection)}</h3><div class="brief-meta">Checked ${esc(humanTime(b.checkedAt))} · ${esc(b.confidence)} confidence</div></div><span class="pill warn">${esc(state)}</span></div><p>${esc(b.prediction)}</p>
      ${line ? `<div class="line-box"><strong>Uncalibrated reference: ${price(line)} · ${(line.probability*100).toFixed(1)}%</strong><br>${esc(line.method)} <a class="source-link" href="${local('pricing.py')}">Calculation ↗</a></div>` : `<div class="brief-meta">Independent numeric line: — · current selection price: —</div>`}
      <ul class="brief-flags">${b.flags.map(f=>`<li>${esc(f)}</li>`).join('')}</ul><div class="brief-sources">${b.officialSources.map(s=>external(s.url,s.label)).join('')}${external(b.olbg,'OLBG event')}</div></article>`;
  }
  function eventSort(a,b) { return (a.official?.start || a.start || '9999').localeCompare(b.official?.start || b.start || '9999'); }
  function active(data) { return data.events.filter(displayable).sort(eventSort); }
  function overview(data,briefs) {
    const rows=active(data), matched=rows.filter(e=>e.official), sampled=rows.filter(e=>e.details?.status==='ok');
    const failedHubs=data.hubs.filter(h=>h.status==='error');
    const failedOfficial=data.officialFeeds.filter(f=>f.status==='error');
    const staleNotice = stale(data.capturedAt) ? notice('Refresh overdue.',`This capture is ${esc(ageText(data.capturedAt))}; odds and event status may no longer be current. Check the linked sources.`) : '';
    const failedNotice = failedHubs.length || failedOfficial.length ? notice('Collection gaps.',`${failedHubs.length} OLBG hub(s) and ${failedOfficial.length} official feed(s) failed. See Flagged for review; failures are not zero-event findings.`) : '';
    const availableBriefs = briefs.filter(b=>briefState(b)==='Needs review').slice(0,2);
    app.innerHTML = `${head('Executive summary','A clearer view of the field','Current OLBG observations, official sources, and research gaps—kept separate from betting recommendations.',action('Review the flags','review.html'))}${staleNotice}${failedNotice}
      <section class="hero"><div class="hero-content"><div class="hero-kicker"><span class="live-dot"></span> Source-first coverage · 15 sports</div><h2>Research with the caveats in view.</h2><p>Prices are a captured OLBG display, not a live offer. Popular selections belong to OLBG’s tipsters; they are not our predictions or win probabilities.</p></div>${action('Explore listings','listings.html',true)}</section>
      <div class="stats">${stat('Upcoming OLBG listings',rows.length,'First rendered hub pages only','calendar')}${stat('Official-source matches',matched.length,'Identity links, not pick clearance','check')}${stat('Independent reference lines',rows.filter(e=>e.researchLine||e.referenceBrief).length,'Review only · uncalibrated','layers')}${stat('Cleared picks',data.publishedPicks.length,'Target: 5 per sport, per day','target')}</div>
      ${section('Browse by sport','Gaelic Sports includes Gaelic football and hurling.','All listings','listings.html')}<div class="sport-grid">${data.sports.map(s=>sportCard(s,rows,data)).join('')}</div>
      ${section('Officially sourced events','A selection of upcoming rows with an event-specific source.','See all listings','listings.html')}<div class="surface">${table(matched.slice(0,8),data,{empty:'No upcoming event-specific crosswalks in this capture.'})}</div>
      ${section('Research notes','Independent, low-confidence leans remain flagged—not cleared picks.','All briefs','briefs.html')}<div class="surface">${availableBriefs.length?availableBriefs.map(briefCard).join(''):'<div class="empty">No fresh research briefs. Historical notes remain available in Research briefs.</div>'}</div>`;
  }
  function filteredPage(data, rows, options={}) {
    const allowed = options.lockSport ? [options.lockSport] : data.sports.map(s=>s.key);
    const dropdown = options.lockSport ? '' : `<label class="field"><span>Sport</span><select id="sport-filter"><option value="">All sports</option>${data.sports.map(s=>`<option value="${esc(s.key)}">${esc(s.name)}</option>`).join('')}</select></label>`;
    const content = `<div class="surface"><div class="filters"><label class="field grow"><span>Search events or selections</span><input id="event-search" type="search" placeholder="Search the captured listings…" autocomplete="off"></label>${dropdown}<label class="field"><span>Official source</span><select id="source-filter"><option value="">All source states</option><option value="matched">Event-specific</option><option value="missing">Needs event match</option></select></label><label class="field"><span>OLBG price</span><select id="price-filter"><option value="">Any price</option><option value="window">−250 to +10000</option></select></label><div class="result-count" id="result-count"></div></div><div id="listing-results"></div><div id="more-results" style="padding:0 18px 18px"></div></div>`;
    const update = () => {
      const q = (document.querySelector('#event-search')?.value || '').trim().toLowerCase();
      const key = document.querySelector('#sport-filter')?.value || '';
      const source = document.querySelector('#source-filter')?.value || '';
      const windowOnly = document.querySelector('#price-filter')?.value === 'window';
      const filtered = rows.filter(e=>allowed.includes(e.sport) && (!key||e.sport===key) && (!source||(source==='matched' ? !!e.official : !e.official)) && (!windowOnly || (e.odds && e.odds.american >= -250 && e.odds.american <= 10000)) && `${e.event||''} ${e.selection||''} ${e.market||''} ${e.competition||''}`.toLowerCase().includes(q));
      let shown = 30;
      const paint = () => { document.querySelector('#listing-results').innerHTML=table(filtered.slice(0,shown),data); document.querySelector('#result-count').textContent=`${filtered.length} listing${filtered.length===1?'':'s'}`; const more=document.querySelector('#more-results'); more.innerHTML=shown<filtered.length?`<button class="button" type="button" id="show-more">Show more (${filtered.length-shown})</button>`:''; document.querySelector('#show-more')?.addEventListener('click',()=>{shown+=30;paint();}); };
      paint();
    };
    setTimeout(()=>{ ['event-search','sport-filter','source-filter','price-filter'].forEach(id=>document.querySelector(`#${id}`)?.addEventListener(id==='event-search'?'input':'change',update)); update(); },0);
    return content;
  }
  function listings(data) {
    const rows = active(data);
    app.innerHTML = `${head('Source inventory','All listings','An incomplete snapshot of OLBG’s first rendered pages. Every row links to an official event or clearly labeled general directory.',action('Review the flags','review.html'))}${notice('Not a live odds feed.','Times and prices can change. An official directory does not confirm a particular event; sampled market details appear only on selected rows.')}${filteredPage(data,rows)}`;
  }
  function sportPage(data,briefs) {
    const sport=data.sports.find(s=>s.key===sportKey);
    if (!sport) { app.innerHTML='<div class="empty">Unknown sport.</div>'; return; }
    const rows=active(data).filter(e=>e.sport===sportKey), hubs=data.hubs.filter(h=>h.sport===sportKey);
    const status=hubs.map(h=>`${h.label}: ${h.status==='ok'?`${h.count} captured`:h.status==='no-tips'?'no tips shown':`unavailable (${h.detail||'error'})`}`).join(' · ');
    const selected=briefs.filter(b=>b.sport===sportKey);
    app.innerHTML = `${head('Sport coverage',sport.name,'Source-linked listings, sampled markets and clearly separated research notes.',action('All sports','index.html'))}
      ${notice('Coverage:',`${esc(status)}. First page only; missing listings do not establish that no events exist.`,true)}
      <div class="stats">${stat('Upcoming listings',rows.length,'OLBG first-page observations','calendar')}${stat('Official-source matches',rows.filter(e=>e.official).length,'Some manual checks may be stale','check')}${stat('Market pages sampled',rows.filter(e=>e.details?.status==='ok').length,'Not all event markets','layers')}${stat('Cleared picks','0','Daily target: at least 5','target')}</div>
      ${section('Listings and market samples','OLBG selection is not an independent recommendation.')}${filteredPage(data,rows,{lockSport:sportKey})}
      ${section('Independent research notes','Low-confidence and held for review.')}<div class="surface">${selected.length?selected.map(briefCard).join(''):'<div class="empty">No event-specific research note has been prepared for this sport.</div>'}</div>`;
  }
  function briefsPage(data,briefs) {
    app.innerHTML = `${head('Independent analysis','Research briefs','These unique, source-linked leans are low confidence and have not passed the publication gate.',action('Review the flags','review.html'))}${notice('No cleared picks.','These dated notes are not the requested high-confidence daily slate. Price, injuries, starting lineups, market settlement and calibration remain incomplete.')}
      <div class="surface">${briefs.map(briefCard).join('')}</div>`;
  }
  function review(data) {
    const rows=active(data), unmatched=rows.filter(e=>!e.official), conflicts=rows.filter(e=>difference(e)!==null&&difference(e)!==0), bad=data.hubs.filter(h=>h.status==='error'), noTips=data.hubs.filter(h=>h.status==='no-tips'), detailErrors=rows.filter(e=>e.details && e.details.status!=='ok');
    app.innerHTML = `${head('Quality & limitations','Flagged for review','The gaps stay visible. An event-specific source link establishes an identity, not a betting recommendation.',action('View listings','listings.html'))}
      ${stale(data.capturedAt)?notice('Snapshot is stale.',`Last captured ${esc(humanTime(data.capturedAt))}. Recheck prices, statuses and all links.`):''}
      <div class="flag-grid"><div class="flag-card"><h3>Daily pick target unmet</h3><p>Zero cleared picks. Four dated low-confidence briefs do not meet the request for five high-confidence picks per sport each day.</p></div><div class="flag-card"><h3>Partial discovery</h3><p>Only first hub pages and at most ${esc(data.limits.eventDetailsPerSport)} event detail pages per sport are captured. Untipped and load-more events can be absent.</p></div><div class="flag-card"><h3>Odds &amp; market rules</h3><p>Displayed prices are timestamped OLBG observations, not bookmaker-specific offers. Settlement, limits, availability and calibration are not established.</p></div><div class="flag-card"><h3>${unmatched.length} source gaps</h3><p>These upcoming OLBG entries link only to a general sport directory; event identity and official timing have not been established.</p></div><div class="flag-card"><h3>${conflicts.length} start-time differences</h3><p>Where both timestamps exist, differing OLBG and official times are displayed side by side. Recheck the official fixture.</p></div><div class="flag-card"><h3>${bad.length} unavailable hubs · ${detailErrors.length} market-page errors</h3><p>There are also ${noTips.length} no-tips pages. An access or parser error is not a claim that a sport has no events; no-tips pages are not complete fixture censuses.</p></div></div>
      ${section('Hub status','Status is per first-page capture; both Gaelic hubs are shown.')}<div class="surface"><div class="table-wrap"><table><thead><tr><th>Hub</th><th>Capture status</th><th>Listings</th><th>Official reference</th><th>OLBG source</th></tr></thead><tbody>${data.hubs.map(h=>{const s=data.sports.find(x=>x.key===h.sport);return `<tr><td><strong>${esc(h.label)}</strong></td><td>${esc(h.status)}<span class="subtle">${esc(h.detail||'')}</span></td><td>${esc(h.count)}</td><td>${external(s.official,s.officialLabel,'General reference, not event confirmation')}</td><td>${external(h.url,'Hub')}</td></tr>`;}).join('')}</tbody></table></div></div>
      ${section('Official feed status','An error means the live schedule or standings could not be used in this capture.')}<div class="surface"><div class="table-wrap"><table><thead><tr><th>Official feed</th><th>Status</th><th>Records</th><th>Source</th></tr></thead><tbody>${data.officialFeeds.map(f=>`<tr><td><strong>${esc(f.name)}</strong></td><td>${esc(f.status)}<span class="subtle">${esc(f.detail||'')}</span></td><td>${esc(f.count ?? '—')}</td><td>${external(f.url,'Official feed')}</td></tr>`).join('')}</tbody></table></div></div>
      ${section('Rows needing official matching or time review','Browse all affected events; the official-directory label is not a fixture confirmation.')} ${filteredPage(data,rows.filter(e=>!e.official || (difference(e)!==null && difference(e)!==0)))}
      ${section('Other open checks','Manual official-source checks are dated and become stale; injuries, lineups and current prices need renewed review.')}<div class="surface pad prose"><p>The old 26 October snapshot incorrectly excluded hurling. This release includes both OLBG Gaelic Football and Hurling hubs. <a class="source-link" href="https://www.gaa.ie/the-gaa/games/our-games" target="_blank" rel="noopener noreferrer">GAA games ↗</a></p><p>Research briefs are independently written and held for review; their historical quotes and time-sensitive facts are not automatically refreshed. <a class="source-link" href="${local('briefs.html')}">Read the briefs →</a></p></div>`;
  }
  function methodology(data) {
    app.innerHTML = `${head('How to read this desk','Methodology','What is captured, what is corroborated, and what is deliberately left blank.',action('View flags','review.html'))}
      <div class="surface pad prose"><h2>1. Discovery is not verification</h2><p>On a scheduled GitHub-hosted run, the collector checks OLBG’s public <a class="source-link" href="https://www.olbg.com/robots.txt">robots.txt ↗</a>, reads one rendered hub response per category, and extracts event names, UTC attributes, most-popular selection, market and American/decimal odds when explicitly present. It does not use OLBG’s disallowed API, bypass access challenges, or crawl load-more endpoints. It samples at most ${esc(data.limits.eventDetailsPerSport)} public event pages per sport for other market/outcome labels and prices. This is not exhaustive.</p>
      <h2>2. Official sources and timing</h2><p>Automated NHL/MLB matches require both team nicknames, league, a unique official fixture and start times within two hours. Any time difference is displayed, not silently reconciled. Other event-specific links are manually checked as of the date shown; after 24 hours they are stale. A general governing-body directory is labeled as such and does not confirm a listing.</p>
      <h2>3. Prices and predictions</h2><p>The OLBG number is a historical observation at the capture time; no bookmaker, market availability, settlement or real-time status is guaranteed. An OLBG tip-share is not a win probability. Independent lines and predictions are blank unless the supporting inputs are recorded. The baseball example combines MLB’s Pythagorean formula with log5; it omits home field and starters. NHL reference lines use each team’s goals for/against per game, independent Poisson scores, and an assumed equal split of tied scores. Standings goals can include overtime/shootout effects, so this is only an approximation of a two-way winner. Neither reference is calibrated or adjusted for injuries, goaltenders or settlement, and both remain review-only.</p>
      <h2>4. Publication gate</h2><p>A cleared pick needs a current exact event, same-selection price and settlement, reproducible and calibrated independent probability, current team/participant availability, and an individual sourced explanation. A quota is not a substitute for evidence. The low-confidence briefs are research notes, not five daily high-confidence picks for each sport.</p>
      <h2>5. Freshness &amp; failures</h2><p>The current snapshot is dated ${esc(humanTime(data.capturedAt))}. A capture older than three hours is marked overdue. Access failures are recorded as errors, never as zero events. A schedule can be delayed or fail; check the source and capture time before use. Current curated briefs are dated and do not update their facts automatically.</p></div>`;
  }
  Promise.all([fetch(local('live.json'),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(`snapshot ${r.status}`);return r.json();}),fetch(local('briefs.json'),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(`briefs ${r.status}`);return r.json();})]).then(([data,briefs])=>{
    if (data.schema !== 'olbg-current/v1' || !Array.isArray(data.events) || !Array.isArray(data.sports)) throw Error('Invalid snapshot schema');
    for (const b of briefs) {
      if (!b.researchLine || briefState(b)!=='Needs review') continue;
      const e=data.events.find(row=>row.sport===b.sport && row.id===b.eventId && row.event===b.event);
      if (e) e.referenceBrief=b;
    }
    renderChrome(data);
    if(page==='home') overview(data,briefs); else if(page==='listings') listings(data); else if(page==='sport') sportPage(data,briefs); else if(page==='briefs') briefsPage(data,briefs); else if(page==='review') review(data); else methodology(data);
  }).catch(error=>{app.innerHTML=`<div class="notice"><div><strong>Snapshot unavailable.</strong> The research data could not be loaded (${esc(error.message)}). This is not evidence that there are no events.</div></div>`;});
})();
