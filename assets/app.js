/* Line-board filter. Progressive enhancement only: with scripting off the
   page still renders every row, because all content is pre-rendered HTML. */
(function () {
  var q = document.getElementById("q");
  if (!q) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll("table.lines tbody tr"));
  var counts = document.getElementById("qcount");
  function apply() {
    var needle = q.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (r) {
      var hit = !needle || (r.getAttribute("data-txt") || "").indexOf(needle) !== -1;
      r.classList.toggle("hide", !hit);
      if (hit) shown++;
    });
    if (counts) counts.textContent = needle ? shown + " of " + rows.length + " rows match" : rows.length + " rows shown";
    document.querySelectorAll("section.sportsec").forEach(function (s) {
      var any = Array.prototype.some.call(s.querySelectorAll("table.lines tbody tr"), function (r) {
        return !r.classList.contains("hide");
      });
      if (s.querySelector("table.lines")) s.classList.toggle("hide", needle && !any);
    });
  }
  q.addEventListener("input", apply);
  apply();
})();
