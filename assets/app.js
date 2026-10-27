// Small table filters. No dependencies, no network calls.
(function () {
  function apply(tableId, term, sport) {
    var table = document.getElementById(tableId);
    if (!table) return;
    var rows = table.tBodies[0].rows;
    var shown = 0;
    for (var i = 0; i < rows.length; i++) {
      var row = rows[i];
      var text = row.textContent.toLowerCase();
      var okTerm = !term || text.indexOf(term) !== -1;
      var okSport = !sport || row.cells[0].textContent.trim() === sport;
      row.style.display = okTerm && okSport ? "" : "none";
      if (okTerm && okSport) shown++;
    }
    var counter = document.querySelector('[data-count="' + tableId + '"]');
    if (counter) counter.textContent = shown + " of " + rows.length + " rows";
  }

  document.addEventListener("DOMContentLoaded", function () {
    var search = document.querySelector('[data-filter="board"]');
    var sport = document.querySelector('[data-filter="board-sport"]');
    function refresh() {
      apply("board", search ? search.value.trim().toLowerCase() : "", sport ? sport.value : "");
    }
    if (search) search.addEventListener("input", refresh);
    if (sport) sport.addEventListener("change", refresh);
    refresh();
  });
})();
