const BASE = document.documentElement.dataset.base || '.';
const json = p => fetch(`${BASE}/${p}`).then(r => { if(!r.ok) throw Error(r.status); return r.json() });
const sportName = (sports, slug) => sports.find(s=>s.slug===slug)?.name || slug;
function eventRows(events, sports){
  if(!events.length) return `<tr><td colspan="7" class="empty"><strong>No publishable selections</strong>Nothing is promoted until an official event source, inputs and original price pass review.</td></tr>`;
  return events.map(e=>`<tr data-search="${(e.event+' '+sportName(sports,e.sport)+' '+e.olbgPick).toLowerCase()}">
    <td><strong>${e.event}</strong><span class="sub">${sportName(sports,e.sport)}</span></td><td>${e.start}</td><td>${e.market}</td>
    <td><strong>${e.olbgPick}</strong><span class="sub">Community listing · ${e.support}</span></td>
    <td class="none">—<span class="sub">Not originated</span></td><td><span class="badge flag">Needs review</span><span class="sub">Official confirmation missing</span></td>
    <td><a class="link" href="${e.url}" target="_blank" rel="noopener">OLBG ↗</a><br><span class="sub">Official: —</span></td></tr>`).join('');
}
function initSearch(){const q=document.querySelector('[data-search-input]');if(!q)return;q.addEventListener('input',()=>{document.querySelectorAll('tbody tr[data-search]').forEach(r=>r.hidden=!r.dataset.search.includes(q.value.toLowerCase()))})}
async function home(){const [sports,events]=await Promise.all([json('data/sports.json'),json('data/events.json')]);
 document.querySelector('#sport-grid').innerHTML=sports.map(s=>{let n=events.filter(e=>e.sport===s.slug).length;return `<a class="card sport-card" href="sports/${s.slug}.html"><div class="sport-top"><span class="icon">${s.icon}</span><span class="count">${n} listing${n===1?'':'s'}</span></div><h3>${s.name}</h3><p>${s.markets}</p></a>`}).join('');
 document.querySelector('#events-body').innerHTML=eventRows(events,sports);document.querySelector('#listing-count').textContent=events.length;document.querySelector('#sport-count').textContent=sports.length;initSearch()}
async function sport(){const slug=document.body.dataset.sport,[sports,events]=await Promise.all([json('data/sports.json'),json('data/events.json')]),s=sports.find(x=>x.slug===slug),mine=events.filter(e=>e.sport===slug);document.title=`${s.name} · OLBG Research Desk`;document.querySelector('#sport-title').textContent=s.name;document.querySelector('#sport-icon').textContent=s.icon;document.querySelector('#markets').textContent=s.markets;document.querySelector('#pricing').textContent=s.pricing;document.querySelector('#olbg-page').href=s.olbg;document.querySelector('#events-body').innerHTML=eventRows(mine,sports);document.querySelector('#listing-count').textContent=mine.length;initSearch()}
window.addEventListener('DOMContentLoaded',()=>document.body.dataset.page==='home'?home():document.body.dataset.page==='sport'?sport():initSearch());
