(() => {
  const input = document.getElementById('query');
  const select = document.getElementById('sport');
  const count = document.getElementById('result-count');
  const rows = Array.from(document.querySelectorAll('#ledger-table tbody tr'));
  if (!input || !select || !count) return;
  function update() {
    const text = input.value.trim().toLocaleLowerCase();
    const sport = select.value;
    let visible = 0;
    rows.forEach((row) => {
      const matches = (!sport || row.dataset.sport === sport) && (!text || (row.dataset.search || '').includes(text));
      row.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = `${visible} ${visible === 1 ? 'record' : 'records'}`;
  }
  input.addEventListener('input', update);
  select.addEventListener('change', update);
})();
