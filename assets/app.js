/* Small progressive-enhancement helpers for the static research desk. */
(function () {
  "use strict";

  var filter = document.getElementById("filter");
  var table = document.getElementById("match-table");
  if (filter && table) {
    var rows = Array.prototype.slice.call(table.tBodies[0].rows);
    var status = document.createElement("p");
    status.className = "filter-count";
    filter.insertAdjacentElement("afterend", status);
    var apply = function () {
      var q = filter.value.trim().toLowerCase();
      var shown = 0;
      rows.forEach(function (row) {
        var hit = !q || row.textContent.toLowerCase().indexOf(q) !== -1;
        row.style.display = hit ? "" : "none";
        if (hit) shown += 1;
      });
      status.textContent = shown + " of " + rows.length + " events shown";
    };
    filter.addEventListener("input", apply);
    apply();
  }

  document.querySelectorAll('a[href^="#"]').forEach(function (link) {
    link.addEventListener("click", function () {
      var el = document.querySelector(link.getAttribute("href"));
      if (el) { el.scrollIntoView({ behavior: "smooth", block: "start" }); }
    });
  });
})();
