/* Offline smoke test: run assets/app.js render paths against the built JSON
 * with a minimal DOM stub. Catches ReferenceError/TypeError in render code. */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const appJs = fs.readFileSync(path.join(ROOT, "assets", "app.js"), "utf8");
const dataDir = path.join(ROOT, "data");

function makeElement(id) {
  return {
    id,
    innerHTML: "",
    textContent: "",
    value: "",
    dataset: {},
    _listeners: {},
    addEventListener(type, fn) { (this._listeners[type] ||= []).push(fn); },
    querySelector() { return null; },
  };
}

function runPage(page, sport) {
  const elements = {};
  const getEl = (id) => (elements[id] ||= makeElement(id));
  const documentStub = {
    getElementById: getEl,
    body: makeElement("body"),
    createElement: (t) => makeElement(t),
  };
  documentStub.body.dataset.page = page;
  documentStub.body.dataset.sport = sport || "";
  const baseDir = page === "sport" ? path.join(ROOT, "sports") : ROOT;
  const fetchStub = async (url) => {
    const clean = String(url).replace(/^https?:\/\/[^/]+/, "");
    const file = path.resolve(baseDir, clean);
    if (fs.existsSync(file)) {
      return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(file, "utf8")) };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  };
  const sandbox = {
    document: documentStub,
    window: { location: { href: `https://site.test/${page === "sport" ? "sports/x.html" : page + ".html"}` } },
    fetch: fetchStub,
    console,
    URL, Intl, Date, Number, String, Object, Array, Math, JSON, Promise,
  };
  sandbox.window.document = documentStub;
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(appJs, sandbox, { filename: "app.js" });
  return new Promise((resolve) => setTimeout(() => resolve(getEl("app").innerHTML), 50));
}

(async () => {
  const pages = [
    ["home", ""], ["matches", ""], ["picks", ""], ["flagged", ""],
    ["sources", ""], ["methodology", ""], ["sport", "basketball"],
    ["sport", "greyhounds"], ["sport", "rugby-union"],
  ];
  let fail = 0;
  for (const [page, sport] of pages) {
    let html = "";
    try {
      html = await runPage(page, sport);
    } catch (e) {
      console.error(`FAIL ${page}/${sport}: ${e.message}`);
      fail = 1;
      continue;
    }
    const problems = [];
    if (html.length < 200) problems.push(`output too short (${html.length})`);
    if (html.includes("Dashboard data could not be loaded")) problems.push("data load error shown");
    if (html.includes("Sport not found.")) problems.push("sport lookup failed");
    if (html.includes("<div class=\"empty\">No rows match") && page !== "sport") problems.push("empty table where rows expected");
    if (page === "sport" && sport && ["greyhounds", "snooker"].includes(sport) && !html.includes("No rows match")) {
      problems.push("empty sport should show empty table");
    }
    if (problems.length) {
      console.error(`FAIL ${page}/${sport}: ${problems.join("; ")}`);
      fail = 1;
    } else {
      console.log(`ok   ${page}/${sport} (${html.length} chars)`);
    }
  }
  // content assertions
  const picks = await runPage("picks", "");
  for (const needle of ["Published picks: 48", "Luke Littler", "MIL Brewers", "Eire Og"]) {
    if (!picks.includes(needle)) { console.error("FAIL picks missing:", needle); fail = 1; }
  }
  const home = await runPage("home", "");
  for (const needle of ["Picks are published and labeled", "48", "Executive summary"]) {
    if (!home.includes(needle)) { console.error("FAIL home missing:", needle); fail = 1; }
  }
  const flagged = await runPage("flagged", "");
  if (!flagged.includes("Skanderborg")) { console.error("FAIL flagged missing Skanderborg flag"); fail = 1; }
  process.exit(fail);
})();
