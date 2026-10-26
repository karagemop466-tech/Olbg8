'use strict';
// Everything essential is pre-rendered. Search and filters are enhancements only.
document.querySelectorAll('[data-filter-panel]').forEach(panel => {
  const table = panel.querySelector('table');
  const rows = Array.from(table.querySelectorAll('tbody tr[data-row]'));
  const search = panel.querySelector('[data-search]');
  const sport = panel.querySelector('[data-sport]');
  const status = panel.querySelector('[data-status]');
  const count = panel.querySelector('[data-result-count]');
  function update() {
    let visible = 0;
    for (const row of rows) {
      const match = (!search || row.textContent.toLowerCase().includes(search.value.toLowerCase())) &&
        (!sport || !sport.value || row.dataset.sport === sport.value) &&
        (!status || !status.value || row.dataset.status === status.value);
      row.hidden = !match;
      if (match) visible++;
    }
    if (count) count.textContent = `${visible} of ${rows.length} rows`;
  }
  [search,sport,status].filter(Boolean).forEach(el => el.addEventListener('input',update));
  const sort = panel.querySelector('[data-sort]');
  if (sort) sort.addEventListener('change',()=>{
    const ordered = [...rows].sort((a,b)=> (sort.value==='sport' ? a.dataset.sport.localeCompare(b.dataset.sport) : a.dataset.name.localeCompare(b.dataset.name)));
    ordered.forEach(row => table.tBodies[0].appendChild(row));
  });
  update();
});
document.querySelectorAll('[data-pick-tab]').forEach(button => button.addEventListener('click',()=>{
  document.querySelectorAll('[data-pick-tab]').forEach(tab => tab.setAttribute('aria-selected', String(tab===button)));
  document.querySelector('#picks-empty-heading').textContent = button.dataset.pickTab === 'today' ? 'No qualifying picks for today' : 'No qualifying upcoming picks';
}));
const snapshot = document.querySelector('[data-snapshot]');
if (snapshot && Date.now() - Date.parse(snapshot.dataset.snapshot+'T23:59:59Z') > 86400000) {
  snapshot.hidden=false;
}
