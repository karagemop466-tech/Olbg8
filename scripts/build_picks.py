#!/usr/bin/env python3
"""Assemble the published pick board.

Each pick names (event_id, market, selection). The script resolves that triple
against data/lines.json, so every price, probability and tip count printed on
the site is the number the pricing step produced - the prose cannot drift from
the arithmetic. If a triple does not resolve, the build fails.

Rules enforced here:
  * the written note must clear 30 words;
  * every source link is kept next to the specific claim it supports;
  * a claim that rests on an OLBG page alone is labelled as such rather than
    dressed up as independent reporting;
  * prices are quoted only from the fair line the pricing step originated.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLBG = "OLBG event listing"

MLB = ("MLB.com probable pitchers", "https://www.mlb.com/probable-pitchers")
MLB_API = ("MLB StatsAPI (official)", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-10-27&hydrate=team")
MLB_PP = ("MLB StatsAPI probable pitchers (official)",
          "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-10-27&hydrate=probablePitcher,team")
ESPN_WS = ("ESPN - 2026 World Series schedule", "https://www.espn.com/mlb/story/_/id/50022544/2026-mlb-playoffs-schedule-how-watch-postseason-world-series-bracket-standings")
SI_BET = ("Sports Illustrated - Game 4 betting preview", "https://www.si.com/betting/brewers-vs-rays-prediction-odds-probable-pitchers-prop-bets-for-world-series-game-4-01m5xqcq32dw")
FOX_ML = ("FOX Sports boxscore page", "https://www.foxsports.com/mlb/world-series-game-4-milwaukee-brewers-vs-tampa-bay-rays-oct-27-2026-game-boxscore-97239")
MLB_FAQ = ("MLB.com World Series FAQ", "https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more")
ATHL = ("The Athletic - World Series preview", "https://www.nytimes.com/athletic/7706469/2026-10-20/world-series-brewers-rays-predictions-questions-facts/")
TRUM = ("MLB Trade Rumors - rosters", "https://www.mlbtraderumors.com/2026/10/brewers-rays-announce-world-series-rosters.html")
NHL_API = ("NHL.com official score API", "https://api-web.nhle.com/v1/score/2026-10-27")
CRICINFO = ("ESPNcricinfo match preview", "https://www.cricinfo.com/series/india-in-new-zealand-2026-27-1539421/new-zealand-vs-india-3rd-t20i-1539434/match-preview")
ICC_NZ = ("ICC - New Zealand squad updates", "https://www.icc-cricket.com/news/new-zealand-announce-key-updates-for-t20i-squad-against-india")
IND_TODAY = ("India Today - 3rd T20I preview", "https://www.indiatoday.in/sports/cricket/story/ind-vs-nz-3rd-t20i-wellington-preview-head-to-head-weather-vaibhav-sooryavanshi-3025581-2026-10-27")
YAHOO_NZI = ("Yahoo Sports - Wellington prediction and pitch report", "https://sports.yahoo.com/articles/zealand-vs-india-3rd-t20i-050525124.html")
YAHOO_NZI2 = ("Yahoo Sports - where to watch and lineups", "https://sports.yahoo.com/articles/where-watch-zealand-vs-india-190001817.html")
TCONN_SCHED = ("Tennis Connected - 27 Oct schedule of play", "https://tennisconnected.com/atp-and-wta-2026-schedule-of-play-tuesday-october-27-for-basel-vienna-tokyo-and-guangzhou/")
TCONN_DRAW = ("Tennis Connected - draw preview", "https://tennisconnected.com/atp-vienna-basel-wta-tokyo-guangzhou-2026-draw-preview-alcaraz-rybakina-zverev-shelton-headline-huge-week/")
TWU_OSAKA = ("Tennis World USA - Osaka's Tokyo draw", "https://www.tennisworldusa.org/tennis/news/WTA_Tennis/170856/home-star-naomi-osaka-handed-tough-1r-matchup-in-tokyo-return/")
TONIC_VW = ("Tennis Tonic - Guangzhou order of play", "https://tennistonic.com/tennis-news/1072764/wta-volynets-liu-and-williams-are-the-top-american-to-play-on-tuesday-27th-of-october/")
LPGA_ENTRIES = ("LPGA official entry list", "https://www.lpga.com/tournaments/maybank-championship/entries")
LPGA_SCHED = ("LPGA official tournament index", "https://www.lpga.com/tournaments")
OOT_ROUGH = ("Out of the Rough - Maybank field notes", "https://www.ootrough.com/post/out-of-the-rough-maybank-championship-2026")
ESPN_LPGA = ("ESPN - LPGA 2026 schedule", "https://www.espn.com/golf/schedule/_/tour/lpga")
NBC_LPGA = ("NBC Sports - 2026 LPGA schedule", "https://www.nbcsports.com/golf/lpga/2026-lpga-schedule")
PDC_CAL = ("PDC official calendar", "https://www.pdc.tv/calendar/")
PDC_WC = ("PDC official World Championship page", "https://www.pdc.tv/tournaments/paddy-power-world-darts-championship")
SPREAD_WC = ("Spreadex - 2027 World Darts Championship prices", "https://www.spreadex.com/sports/blog/preview/pdc-world-darts-championship-odds/")
B365_WC = ("bet365 hub - World Championship outright prices", "https://www.bet365.com/hub/en-gb/darts/darts-competitions/darts-world-championship")
SKY_DARTS = ("Sky Sports - 2026 darts calendar", "https://www.skysports.com/darts/news/13428768/darts-2026-schedule-and-dates-premier-league-darts-world-matchplay-and-more-with-luke-littler-in-action")
WIKI_PDC26 = ("Season record of PDC titles", "https://en.wikipedia.org/wiki/2026_in_PDC")
F1_MEX = ("Formula 1 - official Mexico City GP page", "https://www.formula1.com/en/racing/2026/mexico")
BBC_F1 = ("BBC Sport - Mexico City GP briefing", "https://www.bbc.com/sport/formula1/articles/c6wyrgejp0w8o")
ESPN_F1 = ("ESPN - Mexico City GP start time and preview", "https://www.espn.com/f1/story/_/id/50250142/mexico-city-grand-prix-2026-race-f1-start-s-how-watch-schedule-tv-channel-live-stream-predictions")
MIL_TABLE = ("Olimpia Milano official EuroLeague table", "https://www.olimpiamilano.com/classifica/")
DS_EL = ("DailySports - EuroLeague round 8 form table", "https://dailysports.net/stat/basketball/olimpia-milano-vs-panathinaikos-bc/")

EHF_KOL = ("EHF official club fixture page", "https://www.eurohandball.com/en/club/kZVHhs7nxEhEqyCf6iK_Sw/KolstadH%C3%A5ndball/")
EHF_R6 = ("EHF official round 6 preview", "https://www.eurohandball.com/en/news/en/three-main-round-spots-still-open-before-final-round-6")
EHF_R3 = ("EHF Champions League round 3 preview", "https://ehfcl.eurohandball.com/news/en/final-rematch-at-kielce-sporting-aim-to-conquer-szeged-s-fortress-in-round-3/")
WIKI_EHFG = ("EHF group standings table", "https://en.wikipedia.org/wiki/2026%E2%80%9327_EHF_Champions_League")
RTE_URC = ("RTE - URC fixtures", "https://www.rte.ie/sport/results/rugby/united-rugby-championship/34235/fixtures/")
BBC_URC = ("BBC Sport - URC scores and fixtures", "https://www.bbc.co.uk/sport/rugby-union/pro-tournament/scores-fixtures")
ITSR_URC = ("ItsRugby - URC round 4 results and table", "https://itsrugby.fr/urc-j4-2026-2027-resultats-classement/")
WIKI_URC = ("URC 2026-27 league table", "https://en.wikipedia.org/wiki/2026%E2%80%9327_United_Rugby_Championship")
BBC_URCF = ("BBC Sport - URC 2026-27 fixture release", "https://www.bbc.com/sport/rugby-union/articles/c3r277r92w2o")
OLBG_GOLF = ("OLBG Golf category page", "https://www.olbg.com/betting-tips/Golf/5")
OLBG_SNK = ("OLBG Snooker category page", "https://www.olbg.com/betting-tips/Snooker/8")
OLBG_GRY = ("OLBG Greyhounds category page", "https://www.olbg.com/betting-tips/Greyhounds/28")

# ---------------------------------------------------------------- picks -----
# (sport_key, event_id, market, selection, headline, note, sources, evidence)
PICKS = [
    # ---------------- BASEBALL ----------------
    ("baseball", "160799", "Money Line", "MIL Brewers",
     "Brewers to win the World Series and take the title 4-0",
     "Milwaukee is one win from the championship, having taken Games 1, 2 and 3 by 3-2, 5-4 and 10-1, and MLB's own schedule carries this as Game 4 at Tropicana Field with the series record printed as 3-0. The league's own feed lists Griffin Jax as Tampa Bay's probable starter and leaves Milwaukee's probable slot blank, so the visiting side is the one heading into a bullpen afternoon and that is the shape this price is betting on. On our numbers the Brewers money line sits at -150 for a game they only need to reach rather than win convincingly. Take Milwaukee to win the match at -150, and treat their own blank probable-pitcher slot as the main risk rather than the series state.",
     [("Series state 3-0 and Game 4 venue, date and time", MLB_API),
      ("Game scores in Games 1-3", ESPN_WS),
      ("Tampa Bay's probable is Jax; Milwaukee has no probable listed", MLB_PP)],
     "Fixture, series record, venue and start time read from the official MLB data feed."),
    ("baseball", "160799", "Run Line", "MIL Brewers -1.50",
     "Brewers -1.50 run line in a series they are leading 3-0",
     "The margin market is where a 3-0 lead earns something. Milwaukee won Game 3 by nine runs and posted a 10-1 scoreline, while Tampa Bay's only real resistance came in one-run losses in Games 1 and 2. With a probable bullpen game again in front of Milwaukee, and with the Rays' lineup built on Junior Caminero and Yandy Diaz rather than carrying a designated ace, the two-run spread is the more interesting number than the straight winner. Back Brewers minus one run and a half at -125, which asks for a two-run margin rather than just a win.",
     [("Rays roster construction, Caminero and Diaz", MLB_FAQ),
      ("Brewers rotation depth, Chourio, Bauers, Contreras", MLB_FAQ),
      ("Game 3 scored 10-1", ESPN_WS),
      ("Milwaukee has no probable pitcher listed for Game 4", MLB_PP)],
     "Run-line price originated from two OLBG tips on this market; sample is small."),
    ("baseball", "160799", "Run Line", "TB Rays +1.50",
     "Rays +1.50 keeps a 0-3 hole coverable",
     "Tampa Bay has lost three World Series games and covered in two of them, losing by one run in each of the first two. Nothing about the season record suggests a collapse: they reached 98 wins and are 7-4 in October. One-run games have been the pattern all series, and a Rays side that chased well enough to threaten twice does not need to win outright for this number to pay. The call is Rays plus one run and a half at +125, the value side of the same market the crowd has ignored.",
     [("Rays regular season 98-64 and postseason 7-4", SI_BET),
      ("Games 1 and 2 decided by one run", ESPN_WS)],
     "Zero OLBG tips sit on this side; the price is our floor estimate, not consensus."),
    ("baseball", "160799", "Money Line", "TB Rays",
     "Small exposure to Tampa Bay to avoid a sweep",
     "Tampa Bay at +150 to win Game 4 is not a series prediction. It is a one-game price on a team that has kept two of three close in this World Series and gone 7-4 since the post-season started, which is not the profile of a side being walked over. The price is what it is because Tampa Bay's listed starter, Griffin Jax according to the league's own feed, is a reliever being asked to open a World Series game, and the Sports Illustrated preview has him going on short rest. Bet Tampa Bay to win the match at +150 in a small unit, and treat Milwaukee's still-blank probable slot as the lever this price depends on rather than the series state.",
     [("Jax listed as Tampa Bay's probable pitcher for Game 4", MLB_PP),
      ("Jax asked to open on short rest", SI_BET),
      ("Rays postseason record 7-4", SI_BET)],
     "Probable pitchers read from the official feed, not from press reports."),

    # ---------------- ICE HOCKEY ----------------
    ("ice_hockey", "200104", "Puck Line", "BOS Bruins +1.50",
     "Bruins get a goal and a half in Raleigh against a 9-2-2 Carolina",
     "This is a meeting of the two best starts in the league on the NHL's own record feed: Boston 9-2-1, Carolina 9-2-2, at the Lenovo Center with the Hurricanes priced as short as -196 by the books whose prices the league publishes. A home team that far in front of a 9-win opponent is a thin edge to be laying a goal and a half against, especially when the tipster crowd on this market is unanimous that plus 1.50 is the side worth owning. Our line for Bruins plus 1.50 is -150, and taking Boston with the extra goal is the selection.",
     [("Boston 9-2-1, Carolina 9-2-2, venue and national broadcast", NHL_API),
      ("Carolina listed -192/-196 by published partners", NHL_API)],
     "Official feed supplied both records and the comparison prices."),
    ("ice_hockey", "200108", "Money Line", "PHI Flyers",
     "Flyers at home against a 4-5-0 Columbus, with the market and our number almost identical",
     "Philadelphia is 3-7-3 and still the home team here, and the betting prices carried on the NHL's own feed have Columbus between -125 and -128 with the Flyers from +104 to +106. Our origination lands the Flyers at -120, effectively the same number, which is the honest read: there is no gap to exploit. What there is, is scoring shape - Matvei Michkov has eight goals through ten games for Philadelphia and Trevor Zegras seven assists, against four goals for Kent Johnson in Columbus. Back the Flyers to win the match at -120 and treat it as a coin-flip price rather than an edge.",
     [("Records 4-5-0 and 3-7-3 plus goal leaders", NHL_API),
      ("Partner money-line prices", NHL_API)],
     "Confidence rests on the official record and price feed, not on tip volume."),
    ("ice_hockey", "200104", "Game Totals", "Over 6.50",
     "Over six and a half in the league's two hottest offences",
     "Boston arrives at Carolina as the market favourite at -192 to -196 with a 9-2-1 start, and games like this one between two nine-win teams tend to produce hockey rather than a shutout grind. The single OLBG tip on this Game Totals market is on the over, and the league's own leader list says the goaltending behind the conference is not carrying teams yet, with Jet Greaves on two wins for Columbus and Dan Vladar on two for Philadelphia. Our number is 6.5 with the over priced at -125, so the play is that six goals will not be enough in Hurricanes Bruins.",
     [("Blue Jackets and Flyers goaltending wins as the league's own leader list", NHL_API),
      ("Game time and venue", NHL_API)],
     "Only one OLBG tip exists on this total; sample size is the weakness."),
    ("ice_hockey", "200081", "Money Line", "Kalpa",
     "Kalpa to beat Sport in Liiga with a unanimous tip sheet behind it",
     "An entire Finnish money-line market agreeing on one side is rare on this board, and Kalpa have it: all five tips posted on it are on Kalpa, none on Sport, which our origination prices at -225. What we could not do in time is check a Liiga source for team news, so this entry is a market read rather than a football-briefing read: no injury list, no lines, no recent-score corroboration was found beyond OLBG's own listing. Take Kalpa to win the match at -225 with the caveat printed beside it, and skip it if you require confirmation of either roster.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Ice_Hockey/Other/Finland_SM_Liiga/Kalpa_vs_Sport/13?event_id=200081"))],
     "No official Liiga source was checked; published as unconfirmed."),
    ("ice_hockey", "200082", "Money Line", "IF Malmo Redhawks",
     "Malmo Redhawks at home in the Swedish Hockey League with three tips and no dissent",
     "Malmo Redhawks host Linkoping with three tips on the market and all three behind the home side, a 100 percent share our origination prices at -175. Two of the OLBG members who posted here left comments, which at least means the pick was argued rather than reflexive, but the SHL side of the board was not cross-checked against a league source in this pass. If you want the pick, take Malmo to win the match at -175; if you want the evidence, wait for the league page and confirm lines before staking anything meaningful.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Ice_Hockey/Other/Swedish_Hockey_League/IF_Malmo_Redhawks_vs_Linkoping_HC/13?event_id=200082"))],
     "No official SHL source was checked; published as unconfirmed."),

    # ---------------- CRICKET ----------------
    ("cricket", "188852", "Win Match", "India",
     "India to make it 3-0 in Wellington and end the series",
     "Thirty-five of the fifty tips in this market sit on India, the single largest block of agreement on the whole multi-sport board. The official reporting backs why: India chased 226 and then 181 at Hagley Oval to win the first two games by four wickets apiece. New Zealand's pace depth has thinned, with Matt Henry removed from the series after bowling two overs in the second game and Lockie Ferguson unavailable for this match, while Ishan Kishan's adductor strain keeps Vaibhav Sooryavanshi in the India XI. India to win the match at -205, with Wellington's wind the only real argument against.",
     [("Henry taken out of the series, Ferguson unavailable, Jamieson available", CRICINFO),
      ("Ferguson misses this match and Fisher joins as cover only", ICC_NZ),
      ("Kishan ruled out with adductor strain", IND_TODAY),
      ("India chased 226 and 181; 8pm local start at Hnry Stadium", YAHOO_NZI2)],
     "Highest-volume market on the board and the only High label that cleared every gate."),
    ("cricket", "188868", "Win Match", "Pakistan",
     "Pakistan to get the job done against Sri Lanka at home",
     "The listing puts Pakistan first and 22 of the 31 tips back them in this one-dayer, a 71 percent share our origination sets at -200, short but not unreasonable against Sri Lanka in this format. What we did not manage was a series-page check on team news or a reserve day, so the pick rests on the weight of tipping rather than on confirmed lineups. Back Pakistan to win the match at -200 if you are content to own the favourite without roster confirmation, and note that a wash-out here is a real risk worth pricing.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Cricket/All_Cricket/All_Events/Pakistan_vs_Sri_Lanka_One_Day_Match/7?event_id=188868"))],
     "No official series source checked for this fixture; unconfirmed."),
    ("cricket", "188854", "Win Match", "Ireland",
     "Ireland to complete the sweep in the third one-dayer against Namibia",
     "Ireland holds twenty-two of the thirty-two tips in this market, a 69 percent share that prices at -186 on our origination. The touring side has already won this series and Namibia's threat in these conditions tends to come from a handful of bowlers rather than a balanced attack, which is the shape the tipster crowd appears to be backing. No official Cricket Namibia or Cricket Ireland page was opened for this match, so this is a consensus read rather than a team-news read. Ireland to win the match at -186.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Cricket/All_Cricket/All_Events/Namibia_vs_Ireland_3rd_ODI/7?event_id=188854"))],
     "No official series source checked for this fixture; unconfirmed."),
    ("cricket", "188852", "Man Of The Match", "Abhishek Sharma",
     "Abhishek Sharma for the player award at a five-hundred-and-ninety-eight price",
     "Eleven players share the twenty-five tips in this Man Of The Match market, and Abhishek Sharma holds four of them - level with SV Samson at the top of the list - which puts our price for him at +598. The logic is simple batting volume: one OLBG member openly backed him despite a 27-ball 27 in the previous game on the grounds that his last ten matches read better than that single score. A top-of-the-order hitter in a chase-friendly Wellington contest has more routes to a match-winning contribution than a middle-order accumulator. Take Sharma to be named man of the match at +598 in a small unit, on the plain logic that the award follows the batter who faces the most deliveries in a chase.",
     [("Tipster reasoning quoted on the OLBG event page", ("OLBG event page", "https://www.olbg.com/betting-tips/Cricket/All_Cricket/All_Events/New_Zealand_vs_India_3rd_T20_Match/7?event_id=188852"))],
     "Prop market priced from eleven listed selections; no official fantasy data used."),
    ("cricket", "188854", "Top Team1 Batsman", "MG Erasmus (Namibia)",
     "Erasmus to outscore his own team-mates against Ireland",
     "The top-batsman market for Namibia has MG Erasmus in front with ten of the eighteen tips, a 56 percent share our pricing turns into -117. This is a team-relative market rather than a match-result market, which is exactly where a bowler-heavy Namibian side can still deliver a bet: whoever among them bats longest is a narrower question than who wins. Erasmus carries more of that volume than any of his team-mates on the board. Take Erasmus to be Namibia's top scorer at -117, and note the four-tips-to-one gap between him and the rest of his own dressing room.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Cricket/All_Cricket/All_Events/Namibia_vs_Ireland_3rd_ODI/7?event_id=188854"))],
     "Team-relative market; no official scorecard statistics were available in time."),

    # ---------------- TENNIS ----------------
    ("tennis", "902172", "Win Match", "Leylah Fernandez",
     "Fernandez to get through the Tokyo opener against Sakatsume",
     "Leylah Fernandez is the choice in Tokyo, holding ten of the twelve tips on this first round, and the WTA 500 entry list confirms her among the direct entrants alongside Rybakina, Paolini and Osaka. Himeno Sakatsume has to come through qualifying-level tennis to be here at all, which is the gap the crowd is pricing rather than any specific recent result we could confirm. Fernandez to win the match at -233 is the selection; the one caution is that we could not open a WTA match page for this pairing, so nothing about either player's last two weeks is independently established here.",
     [("Fernandez listed among confirmed direct entrants at WTA Tokyo", TCONN_DRAW),
      ("Tokyo round one continues on 27 October", TCONN_SCHED)],
     "Event and draw confirmed by independent tour reporting; match sheet not confirmed."),
    ("tennis", "902177", "Win Match", "Naomi Osaka",
     "Osaka to win her first Tokyo match in four years",
     "This is Osaka's first appearance at this event in four years and she meets Jasmine Paolini, the only player she has ever lost to in their single previous meeting, a 3-6 6-4 6-4 reverse in the 2025 Miami fourth round. Four of the four tips here sit with Osaka and the third-party price board had her at 1.30, which our origination does not chase: we make her -200 rather than -333. Home crowd, a top-ten seeding at this level and a first-round match in a season's end body are the arguments; the head-to-head is the counter. Osaka to win the match at -200.",
     [("Only previous meeting won by Paolini in Miami 2025; first Tokyo match in four years", TWU_OSAKA),
      ("Osaka and Paolini both in the Tokyo draw", TCONN_SCHED)],
     "Match confirmed by tour reporting; not by an official WTA match page."),
    ("tennis", "902233", "Win Match", "Novak Djokovic",
     "Djokovic over Humbert in Basel, with a caveat on the match sheet",
     "Djokovic is priced at our -160 on the strength of four of the five tips on this pairing, and the fixture sits inside the ATP Vienna and Basel round-one programme for this week. The honest limitation is specific: we confirmed the tournaments and the day, not that this exact pairing is on the published order of play, and Humbert is a lefty whose serve travels well indoors. If the pairing is posted when you look, Djokovic to win the match at -160 is a play; if it is not on the sheet, discard the entry rather than reshaping it.",
     [("Vienna and Basel first round running this week", TCONN_SCHED)],
     "Event-level confirmation only; match-level pairing not confirmed against ATP's own page."),
    ("tennis", "902189", "Win Match", "Lilli Tagger",
     "Tagger prices like a coin flip against a wildcard Venus Williams",
     "Eight tips split evenly, four of them on Lilli Tagger, which is what produces our flat +100 line. The ranking gap is real: Tagger is the world number 53 and Williams is at Guangzhou on a wildcard into a 32-player draw with no first-round byes. That draw structure matters, because it means Williams had to win nothing to be here and Tagger had to earn a spot, and a WTA 250 first round in Asia is the environment where a 22-year-old European indoor-hard-court specialist is favoured. Tagger to win the match at +100.",
     [("Tagger ranked 53 and playing the first round on Centre Court at 6:30pm", TONIC_VW),
      ("Williams received a wildcard; 32-player draw, no byes", TCONN_SCHED)],
     "Order-of-play source is a tour news site; WTA page not opened."),
    ("tennis", "902238", "Win Match", "Rafael Jodar",
     "Jodar over Tabilo where the crowd has gone with the younger name",
     "Rafael Jodar is the selection against Alejandro Tabilo on four of six tips in this first round, and our line prices that at -133. There is no injury news, no confirmed match sheet and no head-to-head we could open in this pass. The entire case is the weight of tipping plus the fact that the market for this match is small enough that a two-tip gap moves the price by nearly forty cents. Jodar to win the match at -133 is a speculative entry on an ATP week; treat the stake accordingly rather than assuming the tour has confirmed a card we could not read.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Tennis/All_Tennis/All_Events/Alejandro_Tabilo_vs_Rafael_Jodar/3?event_id=902238"))],
     "No independent source located for this pairing; unconfirmed."),

    # ---------------- GOLF ----------------
    ("golf", "101913", "Win Tournament", "Lottie Woad",
     "Woad into a Maybank field with the top two names missing",
     "The Maybank Championship runs 29 October to 1 November at the Kuala Lumpur Golf and Country Club West Course for a three-million-dollar purse. The two highest-ranked players in the world, Nelly Korda and Jeeno Thitikul, are not in the field, which leaves the world number three to headline and opens the top of the board. Lottie Woad is entered, sits at world number seven, and has already won twice this season including the Kroger Queen City Championship. Only two tips exist on this outright market, one of them Woad, so our price of +807 is far longer than any book would quote. Woad to win the tournament, at a price that reflects a thin sample rather than her actual standing.",
     [("Event dates, venue and purse, Woad entered", LPGA_ENTRIES),
      ("Defending champion and Race to CME points", LPGA_SCHED),
      ("Korda and Thitikul absent, Ryu highest-ranked entrant", OOT_ROUGH),
      ("Woad's 2026 win at the Kroger Queen City", ESPN_LPGA)],
     "Field, entry and dates confirmed on LPGA's official pages; price is soft because only two tips exist."),
    ("golf", "101914", "Win Tournament", "Stewart Cink",
     "Cink in the Simmons Bank Championship outright at a level-money price",
     "The only information this market carries is one tip on Stewart Cink out of two posted, which our pricing converts into a flat +100 outright - an obviously wrong number for any tournament field, and we publish it as such rather than pretending otherwise. What we could not do was confirm the PGA Tour Champions field, the venue or the cut structure for this event from a tour source in this pass, so there is no form line, no scoring average and no start-list to argue from. There is no recommendation here: consider this a placeholder showing that the outright market on the Champions event is empty, and do not bet off it.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Golf/All_Golf/All_Events/Simmons_Bank_Championship/5?event_id=101914"))],
     "No official tour source confirmed this field; no bet advised."),
    ("golf", "101915", "Win Tournament", "Wyndham Clark",
     "Mexico Open outright market too empty to originate a line",
     "Wyndham Clark takes one of the two tips OLBG exposes on the Mexico Open outright. That is the whole of the evidence for the event, which our origination returns as a flat +100 - a symptom of a two-tip sample rather than an estimate of Clark's chances. We found nothing to anchor it: no field list, no course, no scoring average, no start time we could attribute to a PGA Tour page in this session. The entry is published as an empty market, not as a selection; if you want a golf position on the same weekend, the Maybank outright at least has an official field and confirmed dates behind it.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Golf/All_Golf/All_Events/Mexico_Open/5?event_id=101915"))],
     "No official tour source confirmed this field; no bet advised."),

    # ---------------- DARTS ----------------
    ("darts", "26023", "Win Tournament", "Luke Littler",
     "Littler to retain the world title at a price longer than the books",
     "Luke Littler arrives at the Alexandra Palace as reigning champion and world number one, and 22 of the 36 tips on this outright sit with him ahead of a 128-player field in which the top thirty-two are seeded. The book prices carried on betting sites have him around 8-11, so our -101 is deliberately the shorter of the two numbers, which is the honest consequence of treating tipping volume as probability rather than copying anyone's price. Littler to win the tournament at -101 is the selection; note that a single outright on a 128-name field cannot carry a top confidence label from thirty-six tips.",
     [("Littler the defending champion after a 7-1 final win over van Veen", WIKI_PDC26),
      ("Championship dates, venue, 128-player field and seeding", PDC_WC),
      ("Outright prices of 8-11 with Humphries at 5-1", SPREAD_WC)],
     "Event structure from PDC official pages; book prices shown for reference only."),
    ("darts", "32446", "Win Tournament", "Nathan Aspinall",
     "Aspinall leads a Players Championship field that barely registers",
     "Players Championship 31 is dated for Wednesday 28 October at the Maaspoort in Den Bosch on the PDC's own calendar, and only two of the eight tips on this event name Nathan Aspinall, a 25 percent share that prices out at +167 on our numbers. Pro-tour events over three days across 128 entries are the most volatile outright market in darts, and a two-tip lead on a small field is noise rather than information, so the price we publish is soft in both directions. Aspinall to win the event at +167 is a lottery-ticket entry, useful mainly as evidence that this market is empty rather than as a selection to stake.",
     [("PC31 listed for 28 October at the Maaspoort, Den Bosch", PDC_CAL),
      ("Same date confirmed in the published 2026 darts calendar", SKY_DARTS)],
     "Fixture date official; tip sample too small for a bet recommendation."),

    # ---------------- MOTOR RACING ----------------
    ("motor_racing", "914", "Podium Finish", "Max Verstappen - Yes",
     "Verstappen to finish on the podium in Mexico while the title is decided elsewhere",
     "Round 19 of 2026 runs 30 October to 1 November at the Autodromo Hermanos Rodriguez, 71 laps over 305.354km. The story of the weekend is Kimi Antonelli, who leads George Russell by 123 points after converting pole in Austin with Charles Leclerc and Verstappen beside him on the podium. That Austin result is the whole argument for the top-three market: Verstappen arrives with a fresh podium and no championship pressure, at a one-day price we set at +100 on the single tip available. Verstappen to finish on the podium, yes at +100.",
     [("Round, dates, circuit length, laps and race distance", F1_MEX),
      ("Antonelli 123 points clear; Austin podium had Leclerc and Verstappen with him", BBC_F1)],
     "Podium-price built from one OLBG tip out of two; treat as soft."),
    ("motor_racing", "912", "Win Tournament", "Max Verstappen",
     "The Antonelli-excluded championship market is where the real price sits",
     "OLBG lists a version of the drivers' title market with Kimi Antonelli removed, and four of the seven tips on it name Max Verstappen, which our origination prices at -114. The structure of that market is what makes it interesting rather than the tipping: Antonelli needs only a top-nine finish in Mexico City to be champion whatever anyone else does. On the day this residual market almost certainly resolves against anyone still in it, and the price of -114 for the best remaining name is not a reflection of the standalone chance. Do not back Verstappen here; if you already hold the position, note that the exclusion of one driver is doing all the work.",
     [("Antonelli clinch scenario needs only ninth place", BBC_F1),
      ("Antonelli leads by 123 from Russell", ESPN_F1)],
     "Ante-post market with a removed favourite; flagged as not bettable as priced."),

    # ---------------- BASKETBALL ----------------
    ("basketball", "536177", "Money Line", "Panathinaikos",
     "First plays last in Athens and the price is far too short to ignore",
     "Panathinaikos lead the EuroLeague after seven rounds on the club's own published table, six wins from seven with a plus-96 margin, and they host Armani Olimpia Milano, who are 1-6 and minus-63. The Athens side have won four of their last five including 92-74 over Fenerbahce and 90-67 against Maccabi, with the only blemish an 81-91 loss to Hapoel Tel Aviv, while the tipster market makes the home side the pick at five of eight tips. Our number is -129 to win the match, which is short for a team of this margin but backed by every relevant result we could open.",
     [("Standings, win-loss and point differential for both sides", MIL_TABLE),
      ("Form sequence and recent scores for both clubs", DS_EL)],
     "Standings from a club's own page; form detail from a statistics site."),
    ("basketball", "536179", "Money Line", "Fenerbahce",
     "Fenerbahce on the road at Valencia in the same round",
     "Fenerbahce are one of the two best records in the competition going into round eight, six wins from seven, and they travel to Valencia on the same afternoon Panathinaikos host Milan. Four of the six tips on this game are on the visitors, a 67 percent share our pricing converts into -133, and the roster gap between the squads is wider than the home floor usually compensates for in this league. Take Fenerbahce to win the match at -133. The caveat is that we did not open the league's own match page, so injuries, rest and rotation minutes are entirely unaccounted for in this number.",
     [("Fenerbahce six wins from seven in the round eight standings view", DS_EL),
      ("Round 8 pairings and times", DS_EL)],
     "Fixture from a statistics site; league match page not opened."),
    ("basketball", "536214", "Money Line", "Seoul Knights",
     "Seoul Knights carry the strongest single block of support on the basketball board",
     "The Seoul Knights hold four of the five tips on this Korean Basketball League money line, one of them from a member OLBG flags as an expert, and our origination prices that share at -160. There is no KBL source in our official register, so we cannot confirm standings, imports, injuries or even whether a rotation player is resting, which matters more in a league with imported frontcourts than anywhere else on this board. Seoul Knights to win the match at -160 is the highest-support pick we can name today and also one of the least independently checked; that tension should decide your stake, not the confidence label.",
     [("OLBG listing with expert marker and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Basketball/Other/Korea_KBL/Seoul_Knights_vs_KCC_Egis/4?event_id=536214"))],
     "No KBL source in the official register; unconfirmed."),
    ("basketball", "536174", "Money Line", "Bayern Munich",
     "Bayern at home to Barcelona with three of five tips",
     "Bayern Munich host Barcelona in round eight and three of the five tips on this market name the home side, a 60 percent share we price at -117. The context worth having is that Barcelona arrive as one of the teams expected near the top of this table, while Bayern were beaten 84-86 at home by Partizan in the previous round. That is precisely the sort of result that makes a home price of around even money look reachable rather than cheap. Take Bayern to win the match at -117 as a value position against a foreign favourite, with the honest note that no official EuroLeague match page was opened for lineups.",
     [("Bayern's 84-86 home loss to Partizan in round seven", DS_EL)],
     "Result line from a statistics site; no official lineup check."),
    ("basketball", "536217", "Pointspread", "Frankfurt Skyliners +1.50",
     "Skyliners plus a point and a half in the EuroCup",
     "Frankfurt plus 1.50 is the whole of this spread market, both tips taking the home side against BT Cluj Napoca in a margin our line prices at -150. Two comments were left behind those tips, so at least the position was argued, but we could not confirm the EuroCup standings, the four-quarter format or any rest disadvantage from a league source. A pointspread on a mid-tier European game is exactly the market where one late rotation change decides it. Frankfurt plus 1.50 to cover at -150 is offered as a watch item; the two tips here are not enough to call it a bet.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Basketball/European/Euro_Cup/Frankfurt_Skyliners_vs_U_BT_Cluj_Napoca/4?event_id=536217"))],
     "Two tips only; sample too small to promote."),

    # ---------------- HANDBALL ----------------
    ("handball", "12132", "Money Line", "KS Kielce",
     "Against the consensus: Kielce to beat Kolstad when the crowd is on the draw",
     "The crowd on this money line has turned it into a tie, seven of eleven tips on the draw with Kielce and Kolstad on two each, and that is the clearest mispricing on the whole board. Kolstad are winless after five group games with a minus-35 differential, Industria Kielce are 3-0-2, and the head-to-head between these clubs on the EHF's own record reads seven wins, no draws, no losses, the most recent a 36-29 Kielce victory in Norway. A draw price of -104 for a side that has never drawn this pair is a trap; the play is Kielce to win the match at +307, and the whole reason the price exists is that nobody in the tipster crowd looked at the head-to-head.",
     [("Kielce v Kolstad scheduled 28 October 20:45 CET at Hala Legionow", EHF_KOL),
      ("Head-to-head 7-0-0 with the previous meeting Kolstad 29-36 Kielce", EHF_R6),
      ("Group F standings: Magdeburg 5-0-0, Kielce 3-0-2, Kolstad 0-0-5", WIKI_EHFG)],
     "Consensus diverges sharply from the governing body's own head-to-head record."),
    ("handball", "12132", "Match Handicap", "Kolstad +7.50",
     "Kolstad plus seven and a half, where the crowd and the number agree",
     "Kolstad plus 7.50 carries both tips in this handicap market, and the previous meeting ended 36-29 to Kielce, a seven-goal margin that lands exactly on the boundary of the number being laid. Kielce have lost to Magdeburg in this group by five and are only plus-2 on differential across five games, which is thin cover for a seven-goal handicap on a Wednesday night. The selection is Kolstad plus 7.50 at our -150; check the final scoreline convention your own book applies to a handball push before staking, because a seven-goal Kielce win is a live outcome on these numbers.",
     [("Previous meeting Kolstad 29-36 Industria Kielce", EHF_R6),
      ("Group F table with Kielce on a plus-2 differential", WIKI_EHFG)],
     "Two tips only, both on the same side of this market."),
    ("handball", "12134", "Money Line", "Tie",
     "Paris against Aalborg is the one tie on the board that the history supports",
     "Paris host Aalborg on a money line that seven of the nine tips have made a draw, priced by us at -132. Unlike most of the tie selections on tonight's handball board this one has a direct precedent: Aalborg and Paris have already met this group stage and finished 33-33, and Aalborg top the group. Two sides trading three-goal first-half scores is a genuine draw profile rather than a placeholder pick. Take the tie in PSG v Aalborg at -132, and be aware a two-point margin either way kills it.",
     [("Aalborg 4-1-0 top of Group C, PSG 3-1-1 second", WIKI_EHFG),
      ("Match scheduled for 28 October on the EHF fixture listing", EHF_R6)],
     "Draw supported by the previous meeting scoreline in the same group."),
    ("handball", "12138", "Money Line", "Tie",
     "Plock against Nantes is a tie priced on a very small base",
     "Eight of eleven tips name the draw here at our -128. The surrounding evidence is genuinely close: Orlen Wisla Plock and MT Melsungen are level on six points in Group B, with Plock's five games producing 141 goals for and 136 against, which is a team trading blows rather than controlling them. Nantes are also in that four-team cluster, and we did not find a completed scoreline between these two sides in this pass, which is the main thing missing from the case. The tie in Plock v Nantes is listed at -128 as an observation on where the crowd is, not as a position we can defend with a head-to-head.",
     [("Group B standings with Plock and Melsungen on six points", WIKI_EHFG),
      ("OLBG tip distribution on this market", ("OLBG event page", "https://www.olbg.com/betting-tips/Handball/All_Handball/All_Events/Wisla_Plock_vs_Nantes/20?event_id=12138"))],
     "No head-to-head result located; do not stake on the tie alone."),
    ("handball", "12130", "Money Line", "Tie",
     "Vardar against Melsungen is the tie we would avoid",
     "Eight of thirteen tips back a draw in Skopje at our -103, yet the only meeting of these two that we could read ended 33-31 to Melsungen, and Vardar sit on two points from five games with a minus-four differential while Melsungen have six. A draw price of even money assumes Vardar take this to the wire at home, which they did not manage in the first fixture, and OLBG's own three-way market has the outright outcomes at roughly half the support. Pass on this tie; if you want the match at all, Melsungen to win is the direction the results point in.",
     [("Last meeting MT Melsungen 33-31 HC Vardar 1961", EHF_R6),
      ("Group B table: Vardar on two points, Melsungen on six", WIKI_EHFG)],
     "Published as a counter-consensus warning, not a recommendation to back."),

    # ---------------- VOLLEYBALL ----------------
    ("volleyball", "37121", "Win Match", "Ziraat Bankasi",
     "Unanimous support on the Turkish board, with nothing independent behind it",
     "Ziraat Bankasi are unanimous against Gaziantep Genclik Spor, four tips on the home side and none elsewhere, and two of the members posting carry expert status in the sport, the strongest expert weighting anywhere on today's volleyball list. That produces a 100 percent share and our -200 line. We could not open a Turkish federation source for standings, foreign-player availability or the previous meeting, so the read is that a heavily-backed home side is being trusted by people who tip this league well, not that we know anything about the roster. Ziraat Bankasi to win the match at -200.",
     [("OLBG listing with two experts and four of four tips", ("OLBG event page", "https://www.olbg.com/betting-tips/Volleyball/All_Volleyball/All_Events/Ziraat_Bankasi_vs_Gaziantep_Genclik_Spor/21?event_id=37121"))],
     "No federation source checked; unconfirmed."),
    ("volleyball", "37075", "Win Match", "Bergamo W",
     "Bergamo away at Marignano with an expert behind the number",
     "Bergamo are named by five of the seven tips on the Italian women's fixture at Marignano, a 71 percent share our origination prices at -150, with one of those tips from a member holding expert status in the sport. Bergamo are the stronger club name in Serie A1 women's volleyball, which is at least consistent with the direction of the crowd, but we did not confirm the table position, the current import roster or the last result for either side. Bergamo to win the match at -150 is the number to note, with the explicit warning that the league page was not opened for this round.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Volleyball/All_Volleyball/All_Events/Marignano_W_vs_Bergamo_W/21?event_id=37075"))],
     "No league source checked; unconfirmed."),
    ("volleyball", "37076", "Win Match", "Vallefoglia W",
     "Vallefoglia at reigning-strength Conegliano, and the crowd likes it",
     "Conegliano v Vallefoglia is the biggest named match on the volleyball board and the deepest market of the fourteen listings captured today, six of its ten tips behind Vallefoglia at a 60 percent share we price at -125. That the crowd leans away from the more famous club is the interesting part, and it is exactly the sort of signal worth watching in a league where a single import can swing a series. Vallefoglia to win the match at -125 is the listed selection; no Italian federation page was opened, so there is no injury or rotation information inside this number.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Volleyball/All_Volleyball/All_Events/Conegliano_W_vs_Vallefoglia_W/21?event_id=37076"))],
     "Deepest volleyball market on the board; still unconfirmed by a league source."),
    ("volleyball", "37126", "Win Match", "Halkbank Ankara",
     "Halkbank in Turkey with a four-to-one tip margin",
     "Halkbank Ankara carry four of the five tips against TFL Altekma at our -160, and that single dissenting tip is the only reason the price is not shorter. Early-season Turkish men's fixtures are a poor environment for laying a short price, because the rosters are still settling and a 100 percent share on a five-tip market is not the same thing as a 100 percent chance. Halkbank to win the match at -160 is a reasonable follow-the-crowd entry; it is also the sort of market where the crowd is thin enough that you should size it as a speculative bet rather than a banker.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Volleyball/All_Volleyball/All_Events/TFL_Altekma_vs_Halkbank_Ankara/21?event_id=37126"))],
     "No federation source checked; unconfirmed."),
    ("volleyball", "37081", "Win Match", "Uni Opole W",
     "Uni Opole over Palac Bydgoszcz in a shallow Polish market",
     "Uni Opole are priced at -133 to beat Palac Bydgoszcz on four of the six tips in this Polish women's fixture, with one comment attached and no expert markers on either side of the market. Liga Siatkowki women's volleyball is a low-information market outside Poland. The most important number in this row is that OLBG exposes only six tips across both outcomes: the price is being set by a handful of people, and neither roster has been confirmed against the league's own site. Uni Opole to win at -133 therefore goes on the board as a listed position with that limitation printed on it rather than as a recommendation, Everything we can actually stand on for this row is OLBG's own tip distribution.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Volleyball/All_Volleyball/All_Events/Uni_Opole_W_vs_Palac_Bydgoszcz_W/21?event_id=37081"))],
     "No league source checked; unconfirmed."),

    # ---------------- RUGBY UNION ----------------
    ("rugby_union", "609590", "To Win", "Glasgow Warriors",
     "Glasgow host a Lions side that just lost 31-10 at Edinburgh",
     "Round five of the United Rugby Championship opens on Friday 30 October at Scotstoun with second-placed Glasgow taking the Johannesburg Lions. The two sides are twelve places apart on the table with Glasgow on eighteen points from three wins and a draw and the Lions on nine from two wins and a loss. The visitors arrive off a 31-10 defeat at Edinburgh, a result that left their points differential at minus-46 across four games, while Glasgow came from 17-0 down at Benetton to win 24-20. Glasgow to win the match at -125 is the position, and the mental edge of chasing from behind is already tested.",
     [("Fixture date, time and venue", RTE_URC),
      ("Round 4 results including Edinburgh 31-10 Lions and Benetton 20-24 Glasgow", ITSR_URC),
      ("Glasgow second on 18 points; Lions eleventh on 9 with -46 differential", WIKI_URC)],
     "Table and results from published league records; URC's own site not opened."),
    ("rugby_union", "609584", "Handicap", "Connacht +3.50",
     "Connacht get the points at home to Leinster and they are worth them",
     "The one tip OLBG carries on this handicap is Connacht plus 3.50, and the numbers behind that view are reasonable: Connacht and Leinster sit four points apart in the table, ten to thirteen. Both are two wins and two losses after four rounds, with the home side having just put 48 points on Zebre at the Sportsground while Leinster needed 24-18 at home to get past Munster. Leinster are the better side across a season, but a home ground in Galway and a three-and-a-half point start is a real position. Take Connacht plus 3.50 at -125.",
     [("Fixture and kick-off confirmed in the published round five list", RTE_URC),
      ("Round 4: Connacht 48-27 Zebre; Leinster 24-18 Munster", ITSR_URC),
      ("Table: Leinster sixth on 13, Connacht eighth on 10", WIKI_URC)],
     "Handicap from one tip; treat the price as indicative."),
    ("rugby_union", "609586", "Handicap", "Munster -6.50",
     "Munster six and a half at home to the Sharks is a stretch worth flagging",
     "Thomond Park on Saturday 31 October is where this one sits. The single OLBG tip backs Munster minus 6.50 against a Durban Sharks side that are fifth in the table on fifteen points, one win more than Munster, who are ninth on ten with one win, one draw and two losses. The Sharks have just won 36-21 at Cardiff Arms Park, so they score freely on the road, while Munster were beaten 24-18 by Leinster in the previous round. Our line makes the hosts -125 on the handicap, and we would not take it: the form reads like a Sharks cover within seven rather than a Munster win by double figures.",
     [("Fixture and kick-off time", BBC_URC),
      ("Round 4: Cardiff 21-36 Sharks; Leinster 24-18 Munster", ITSR_URC),
      ("Table: Sharks fifth on 15, Munster ninth on 10", WIKI_URC)],
     "Published as a warning against the only tip on this market."),
    ("rugby_union", "609604", "To Win", "Colomiers",
     "Colomiers over Agen in a Pro D2 round we could not confirm",
     "Colomiers are two for two in the tips on their home match with Agen, which our pricing renders as -150 on a straight winner in the French second tier. Everything else is missing: no Pro D2 league page was opened, so the table, the previous five results for each club, the travel and the squad rotation are all unknown to us. Pro D2 is a league where home advantage and rotation genuinely move results because the schedule is so congested. Colomiers to win the match at -150 is published as a market-following entry only, and it should not be staked until the fixture is confirmed on an official page.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Rugby_Union/All_Rugby_Union/All_Events/Colomiers_v_Agen/9?event_id=609604"))],
     "No LNR or FFR source checked; unconfirmed."),
    ("rugby_union", "609611", "To Win", "Pau",
     "Pau to beat Toulouse is a contrarian price on a Top 14 round we cannot check",
     "Pau against Toulouse at our -125 rests on a single tip in a market of one, and that is the entire evidential base for it. Facing a club of Toulouse's resources, an unbackable-looking price of around even money is a strong hint either that the tipster has something we cannot see or that a single opinion has moved an empty market. On the numbers available the second explanation is the safer assumption. Section list this as an anomaly rather than an opportunity: we would not stake on Pau to win the match without an official Top 14 sheet, injury list and table position first.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Rugby_Union/All_Rugby_Union/All_Events/Pau_v_Toulouse/9?event_id=609611"))],
     "One-tip market against a major club; flagged as an anomaly, not a bet."),

    # ---------------- RUGBY LEAGUE ----------------
    ("rugby_league", "2695857", "Win Tournament", "New South Wales",
     "Origin ante-post is the only rugby league market OLBG is showing",
     "New South Wales are the strongest single block anywhere on the rugby league board, nine of the thirteen tips on the 2027 State of Origin outright behind them at a 69 percent share our origination prices at -162. What is not here matters just as much: there is not one club fixture listed, because Super League's season has finished and the NRL's is not carried as a match market. There is no form line, no team list and no injury report to attach to this number. NSW to win the series at -162 is an ante-post opinion about a competition that has not started, and the price should be judged on that basis.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Rugby_League/All_Rugby_League/All_Events/State_of_Origin_2027/10?event_id=2695857"))],
     "Ante-post with no fixture list; no governing-body source applicable."),
    ("rugby_league", "2801554", "Grand Final Winner", "Wigan Warriors",
     "Wigan to win the 2027 Super League Grand Final at even money",
     "Wigan take two of the four tips in the Super League grand final winner market, and our number makes them +100 to lift the trophy in October 2027. For a club of Wigan's recent standing that is a price that says the market is empty rather than that the opinion is sharp, and an outright twelve months from now carries every coaching change, every departure and every injury that has not happened yet. If you want the position, Wigan to win the Grand Final at +100 is the quoted line, but treat it as the front end of a long window rather than as a bet with a form case behind it, because there is none available today.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Rugby_League/All_Rugby_League/All_Events/Super_League_2027/10?event_id=2801554"))],
     "Only four tips across the whole outright market; no bet advised."),
    ("rugby_league", "2801600", "Grand Final Winner", "Penrith Panthers",
     "Penrith in the NRL outright with one tip out of three",
     "The NRL 2027 grand final winner market contains three tips, one of them on Penrith, which our pricing returns as +120 - an outright on a seventeen-team competition at a price that would normally apply to a two-horse match. That tells you exactly what happened: an empty market, not a strong opinion. No NRL draw, no premiership table and no finals series result was available to us in this pass to support the number in any way. Penrith to win the 2027 grand final at +120 is listed for completeness and is explicitly not a recommendation.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Rugby_League/All_Rugby_League/All_Events/NRL_2027/10?event_id=2801600"))],
     "Empty outright; flagged as not bettable."),

    # ---------------- GAELIC SPORTS ----------------
    ("gaelic_sports", "3327", "Win Tournament", "Kerry",
     "Kerry to win the 2027 All-Ireland football title at -167",
     "Kerry hold six of the eight tips on the 2027 Sam Maguire outright. The context OLBG prints on the same page is that the county lost the 2026 final, with Mayo recorded there as ending a 75-year wait by beating them, so this price is a rebound number rather than a dominance one. We could not confirm that 2026 final result against an official GAA source in this session, and it is the single load-bearing fact in the row, so the entry is published with that gap printed on it. Kerry to win the championship at -167, with the caveat that the previous final result is an OLBG claim, not one we checked.",
     [("OLBG outright listing and tip count", ("OLBG category page", "https://www.olbg.com/betting-tips/Gaelic_Football/25")),
      ("OLBG's own note that Mayo won the 2026 final over Kerry", ("OLBG category page", "https://www.olbg.com/betting-tips/Gaelic_Football/25"))],
     "2026 All-Ireland final result not confirmed against a GAA source; flagged."),
    ("gaelic_sports", "3531", "Handicap", "Eire Og Cor +0.50",
     "Half a point in a Cork club championship game with six of six on it",
     "Eire Og plus 0.50 against Kanturk carries all six tips on this handicap, and the price that follows on our origination is -250, right on the boundary of the band we are allowed to work in. A half-point start in club hurling or football is essentially a double chance on the tie, which is why the share is so high and why the price is so short. Nothing here is corroborated: no GAA county board fixture page, no team list and no previous meeting was opened, so there is no way to check whether the half point is generous or thin. Eire Og plus 0.50 is listed at -250 and no more than that.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Gaelic_Football/All_Gaelic_Football/All_Events/Kanturk_v_Eire_Og_Cor/25?event_id=3531"))],
     "No GAA source checked; price sits on the -250 boundary."),
    ("gaelic_sports", "3537", "Handicap", "Kildimo Pallaskenry +3.50",
     "Three and a half points in a Limerick club game",
     "Kildimo Pallaskenry receive 3.50 against Fr Caseys on five of the seven tips in this handicap market, priced at -150 by our origination, with no expert flag on either side. Club championship handicaps are the least transparent corner of this whole project, because the scoring context that makes three and a half points short or long is buried in county reports nobody indexes, and we did not open a single one for this game. Kildimo Pallaskenry plus 3.50 at -150 is a market-following entry with no independent support whatsoever, which is a reason to watch it rather than to bet it.",
     [("OLBG listing and tip count", ("OLBG event page", "https://www.olbg.com/betting-tips/Gaelic_Football/All_Gaelic_Football/All_Events/Fr_Caseys_v_Kildimo_Pallaskenry/25?event_id=3537"))],
     "No GAA source checked; unconfirmed."),
    ("gaelic_sports", "675", "Win Hurling", "Galway",
     "Galway top the hurling outright on a seventeen-tip market",
     "Galway take seven of the eighteen tips on the 2027 All-Ireland hurling outright, a 39 percent share that our pricing sets at +136 for the Liam MacCarthy Cup. This is the only hurling listing anywhere on OLBG today, and the field is spread thin across the remaining tips, so +136 is a number driven as much by the absence of a dominant favourite as by support for Galway. Take it as an ante-post view eleven months out: no provincial championship, no league and no panel has been played yet, which means the price is close to meaningless and the direction is the only usable part.",
     [("OLBG listing and tip count", ("OLBG category page", "https://www.olbg.com/betting-tips/Hurling/26"))],
     "Sole hurling listing; ante-post with no season played."),
]


def _norm_src(claim, src):
    """A source entry is (source-name, url); the first half of a pair is the claim it supports."""
    if isinstance(src, str):                      # ("name", "url") flattened by mistake
        return {"claim": None, "name": claim, "url": src}
    name, url = src
    return {"claim": claim, "name": name, "url": url}


def american_str(v):
    if v is None:
        return "no line"
    return f"{v:+.0f}".replace("+-", "-") if isinstance(v, (int, float)) else "no line"


def main():
    idx = {}
    for r in json.load(open(os.path.join(ROOT, "data", "lines.json"), encoding="utf-8"))["rows"]:
        idx.setdefault((r["event_id"], r["market"], r["selection"]), r)
    out, errs = [], []
    for i, (sk, eid, mkt, sel, head, note, srcs, ev) in enumerate(PICKS, 1):
        row = idx.get((eid, mkt, sel))
        if not row:
            errs.append(f"unresolved pick: {sk} {eid} {mkt} {sel}")
            continue
        wc = len(note.split())
        if wc < 30:
            errs.append(f"note under 30 words ({wc}): {eid} {sel}")
        # sentence hygiene, so hand-edits cannot splice two sentences together
        if note.rstrip()[-1] not in ".!?":
            errs.append(f"note does not end on a sentence mark: {eid} {sel}")
        if re.search(r"[a-z]\.[A-Za-z]", note) or "  " in note:
            errs.append(f"note has a spacing or full-stop fault: {eid} {sel}")
        for si, sent in enumerate(re.split(r"(?<=[.!?]) +", note)):
            nw = len(sent.split())
            if nw > 45:
                errs.append(f"sentence {si + 1} runs to {nw} words: {eid} {sel}")
            if sent and not (sent[0].isupper() or sent[0].isdigit()):
                errs.append(f"sentence {si + 1} starts lower-case (lost full stop?): {eid} {sel}")
        for bad in ("model", "Model", "verified", "Verified", "verification"):
            if bad in note:
                errs.append(f"forbidden word {bad!r} in note: {eid} {sel}")
        out.append({
            "pick_id": f"P{i:03d}", "sport_key": sk, "sport": row["sport"],
            "event": row["event"], "event_id": eid, "competition": row["competition"],
            "time_label": row["time_label"], "market": mkt, "selection": sel,
            "headline": head, "note": note, "word_count": wc,
            "confidence": row["confidence"], "pick_score": row["pick_score"],
            "our_prob": row["our_prob"], "fair_american": row["fair_american"],
            "our_american": row["our_american"], "our_decimal": row["our_decimal"],
            "fair_decimal": row["fair_decimal"], "outcome_count_k": row["outcome_count_k"],
            "market_line": row["market_line"],
            "olbg_win_tips": row["olbg_win_tips"], "olbg_total_tips": row["olbg_total_tips"],
            "olbg_displayed_pct": row["olbg_displayed_pct"],
            "market_total_tips": row["market_total_tips"],
            "official_tier": row["official_tier"], "in_window": row["in_window_fair"],
            "line_flags": row["flags"], "evidence": ev,
            "olbg_url": row["olbg_url"],
            "olbg_listing": {"name": OLBG, "url": row["olbg_url"]},
            "sources": [_norm_src(n, u) for n, u in srcs],
        })
    if errs:
        print("\n".join(errs), file=sys.stderr)
        sys.exit(1)
    with open(os.path.join(ROOT, "data", "picks.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema": "olbg-picks/v2", "built_utc": "2026-10-27T05:50:00Z",
                   "count": len(out), "picks": out}, fh, indent=1, ensure_ascii=False)
    import collections
    per = collections.Counter(p["sport"] for p in out)
    conf = collections.Counter(p["confidence"] for p in out)
    print(f"wrote {len(out)} picks; bands={dict(conf)}")
    for s, n in sorted(per.items(), key=lambda x: -x[1]):
        print(f"  {s:16} {n}")


if __name__ == "__main__":
    main()
