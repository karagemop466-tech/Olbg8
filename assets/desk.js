
/* Progressive enhancement: table filters only. All content is in the HTML. */
(() => {
  "use strict";
  const tables = [...document.querySelectorAll("table.data-table")];
  const wire = (table) => {
    const id = table.id;
    const search = document.querySelector(`[data-filter="${id}"]`);
    const sport = document.querySelector(`[data-filter-sport="${id}"]`);
    const count = document.querySelector(`[data-count="${id}"]`);
    const rows = [...table.querySelectorAll("tbody tr")];
    if (!search && !sport) return;
    const update = () => {
      const q = (search?.value || "").trim().toLowerCase();
      const sp = sport?.value || "";
      let shown = 0;
      for (const row of rows) {
        const ok = (!q || (row.dataset.search || "").includes(q)) &&
                    (!sp || row.dataset.sport === sp);
        row.hidden = !ok;
        if (ok) shown++;
      }
      if (count) count.textContent = `${shown} of ${rows.length} rows`;
    };
    search?.addEventListener("input", update);
    sport?.addEventListener("change", update);
    update();
  };
  tables.forEach(wire);
  // Flagged page severity filter.
  const sev = document.getElementById("severity-filter");
  if (sev) {
    sev.addEventListener("change", () => {
      for (const row of document.querySelectorAll("#flags-table tbody tr")) {
        row.hidden = Boolean(sev.value) && row.dataset.level !== sev.value;
      }
    });
  }
})();
