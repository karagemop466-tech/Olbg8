import json
from pathlib import Path
specs=[
('Golf','Golf',5,'Strokes-gained, course fit, field strength, tee times, weather; simulate correlated round scores.','Outright, place, first-round leader, head-to-head'),
('Volleyball','Volleyball',21,'Opponent-adjusted side-out and break rates; point-to-set-to-match recursion with lineup effects.','Winner, set handicap, points handicap, totals'),
('Rugby Union','Rugby_Union',9,'Possessions, tries, conversion and penalty rates; joint score simulation with home and lineup effects.','Winner including draw, handicap, points total'),
('Cricket','Cricket',7,'Format-specific ball outcomes, wickets, venue and toss; innings simulation including rain and tie rules.','Winner, runs handicap, innings totals, player markets'),
('Snooker','Snooker',8,'Opponent-adjusted frame win rates with format-specific first-to-N recursion.','Winner, frame handicap, correct score, outright'),
('Darts','Darts',15,'Hold/break rates, checkout and scoring by throw order; legs-to-sets recursion.','Winner, legs/sets handicap, totals, outright'),
('Baseball','Baseball',12,'Pitcher and bullpen adjusted run distributions, park and lineup effects; extra-inning rules.','Money line, run line, game totals'),
('Gaelic Sports','Gaelic_Football',25,'Gaelic Football scoring and competition-specific draw rules; Hurling is explicitly excluded from this site.','Winner, handicap, total points, outright'),
('Greyhounds','Greyhounds',28,'Track/distance adjusted sectional and finish-time distributions, trap, grade, interference and withdrawals.','Race win, place where offered'),
('Tennis','Tennis',3,'Surface and opponent adjusted serve/return point rates; game, tiebreak, set and match recursion.','Winner, games/sets handicap, totals, outright'),
('Motor Racing','Motor_Racing',14,'Circuit-adjusted qualifying and race pace; simulate reliability, grid, weather and safety-car uncertainty.','Race win, podium, top six, points, fastest lap, outright'),
('Handball','Handball',20,'Pace, attack/defence efficiency and goalkeeper save rates; joint score distribution.','Three-way winner, handicap, totals'),
('Ice Hockey','Ice_Hockey',13,'Shot quality, goalie, special-teams and rest effects; regulation scoring and separate overtime simulation.','Money line, regulation, puck line, game totals'),
('Basketball','Basketball',4,'Possession pace and opponent-adjusted efficiency; lineup and rest effects in joint score simulation.','Money line, pointspread, total points'),
('Rugby League','Rugby_League',10,'Set completion, field position, tries and kick rates; score distribution with golden-point rules.','Winner, handicap, points total, outright')]
sports=[]
for name,slug,n,method,markets in specs:
 sports.append(dict(name=name,slug=slug,id=n,url=f'https://www.olbg.com/betting-tips/{slug}/{n}',checked='2026-10-26',method=method,markets=markets,pricing_status='Specification only — not fitted or calibrated',coverage='Partial page extraction; pagination not exhausted'))
rows=[]
def add(sport,group,entries):
 s=next(s for s in sports if s['name']==sport)
 for eid,name,display,market in entries:
  slug=name.replace(' ','_')
  rows.append(dict(sport=sport,event_id=str(eid),event=name,display_time=display,market=market,source=f"https://www.olbg.com/betting-tips/{s['slug']}/{group}/{slug}/{s['id']}?event_id={eid}",observed_on='2026-10-26',start_utc=None,official_source=None,official_fact=None,selection=None,confidence=None,american_odds=None,fair_decimal=None,prediction=None,status='Unverified — research only',flags=['No executable price captured','No sourced current form, statistics or availability assessment','Absolute start and eligibility not confirmed']))
add('Golf','All_Golf/All_Events',[(101913,'Maybank Championship','01 Nov 06:45','Win Tournament'),(101915,'Mexico Open','01 Nov 17:45','Win Tournament'),(101914,'Simmons Bank Championship','01 Nov 17:45','Win Tournament')])
add('Volleyball','All_Volleyball/All_Events',[(37101,'Montes Claros vs Sada Cruzeiro','Today 22:00','Win Match'),(37004,'Sancor Volei W vs SESI Volei Bauru W','Today 21:30','Win Match')])
add('Volleyball','All_Volleyball/All_Events',[(37076,'Conegliano W vs Vallefoglia W','28 Oct 19:00','Win Match'),(37075,'Marignano W vs Bergamo W','Tomorrow 19:00','Win Match'),(37081,'Uni Opole W vs Palac Bydgoszcz W','Tomorrow 19:30','Win Match'),(37121,'Ziraat Bankasi vs Gaziantep Genclik Spor','Tomorrow 16:00','Win Match'),(37129,'VaLePa vs AC Oulu','Tomorrow 16:30','Win Match')])
add('Rugby Union','All_Rugby_Union/All_Events',[(609604,'Colomiers v Agen','30 Oct 14:00','To Win'),(609603,'Montauban v Narbonne','30 Oct 14:30','To Win'),(609598,'Oyonnax v Soyaux Angouleme','30 Oct 14:30','To Win'),(609605,'Dax v Provence','29 Oct 16:00','Handicap'),(609599,'Beziers v Grenoble','30 Oct 14:30','To Win'),(609600,'Nissa v Aurillac','30 Oct 14:30','To Win'),(609590,'Glasgow Warriors v Lions','30 Oct 15:45','To Win'),(609584,'Connacht v Leinster','30 Oct 15:45','Handicap')])
add('Cricket','All_Cricket/All_Events',[(188852,'New Zealand vs India 3rd T20 Match','Tomorrow 03:00','Win Match'),(188854,'Namibia vs Ireland 3rd ODI','Tomorrow 03:30','Win Match'),(188868,'Pakistan vs Sri Lanka One Day Match','Tomorrow 04:00','Win Match'),(188872,'Afghanistan vs Zimbabwe 1st T20 Match','Tomorrow 10:30','Win Match'),(188864,'Melbourne Stars W vs Hobart Hurricanes W T20 Big Bash','29 Oct 04:10','Win Match'),(188865,'Brisbane Heat W vs Sydney Sixers W T20 Big Bash','30 Oct 04:10','Win Match'),(188835,'South Africa vs Australia','31 Oct 04:30','Win Match'),(188876,'Auckland vs Canterbury One Day Match','Tomorrow 17:30','Win Match')])
add('Darts','All_Darts/All_Events',[(26023,'PDC World Championship 2027','03 Jan 2027 12:00','Win Tournament'),(32446,'Players Championship 31','28 Oct 08:00','Win Tournament')])
add('Baseball','MLB/MLB',[(160795,'MIL Brewers @ TB Rays','Tomorrow 00:00','Money Line; Run Line ±1.50; Game Totals 7.50')])
add('Gaelic Sports','All_Gaelic_Football/All_Events',[(3531,'Kanturk v Eire Og Cor','01 Nov 09:00',''),(3537,'Fr Caseys v Kildimo Pallaskenry','01 Nov 10:30',''),(3327,'All Ireland Football Championship 2027','25 Jul 2027 10:30','')])
add('Greyhounds','All_Greyhounds/All_Events',[(690271,'8:24 Towcester','Today 16:24','Daily Races'),(690274,'8:36 Nottingham','Today 16:36','Daily Races'),(690275,'8:34 Harlow','Today 16:34','Daily Races'),(690276,'8:41 Towcester','Today 16:41','Daily Races'),(690277,'8:47 Yarmouth','Today 16:47','Daily Races'),(690284,'9:16 Towcester','Today 17:16','Daily Races'),(690285,'9:23 Yarmouth','Today 17:23','Daily Races'),(690288,'9:46 Nottingham','Today 17:46','Daily Races')])
add('Tennis','All_Tennis/All_Events',[(902381,'Aliaksandra Sasnovich vs Nikola Bartunkova','Tomorrow 01:00','Win Match'),(902172,'Leylah Fernandez vs Himeno Sakatsume','Tomorrow 02:00','Win Match'),(902189,'Lilli Tagger vs Venus Williams','Tomorrow 03:30','Win Match'),(902232,'Stan Wawrinka vs Jiri Lehecka','Tomorrow 14:30','Win Match'),(902233,'Novak Djokovic vs Ugo Humbert','28 Oct 06:00','Win Match'),(902238,'Alejandro Tabilo vs Rafael Jodar','Tomorrow 09:00','Win Match'),(902176,'Ann Li vs Ekaterina Alexandrova','Today 22:00','Win Match'),(902240,'Alex Michelsen vs Botic Van De Zandschulp','Tomorrow 10:00','Win Match')])
add('Motor Racing','All_Motor_Racing/All_Events',[(912,'Formula 1 Drivers Championship 2026 Without Kimi Antonelli','06 Dec 08:00','Win Tournament'),(914,'Mexico City Grand Prix','01 Nov 15:00','Top 6 Finish')])
add('Handball','All_Handball/All_Events',[(12136,'SC Magdeburg vs HC Kriens Luzern','28 Oct 19:45','Money Line'),(12132,'KS Kielce vs Kolstad','28 Oct 19:45','Money Line'),(12128,'Fuchse Berlin vs RK Partizan','29 Oct 17:45','Money Line'),(12130,'HC Vardar vs MT Melsungen','28 Oct 17:45','Money Line'),(12138,'Wisla Plock vs Nantes','28 Oct 17:45','Money Line'),(12127,'FC Porto vs Veszprem','28 Oct 17:45','Money Line'),(12135,'RK Celje vs RK Zagreb','28 Oct 19:45','Money Line'),(12134,'PSG Handball vs Aalborg Handbold','28 Oct 19:45','Money Line')])
add('Ice Hockey','NHL/NHL',[(200101,'LA Kings @ NY Rangers','Today 19:07','Money Line'),(200103,'TOR Maple Leafs @ CGY Flames','Today 20:37','Money Line'),(200102,'DET Red Wings @ EDM Oilers','Today 21:37','Money Line'),(200104,'BOS Bruins @ CAR Hurricanes','Tomorrow 20:07','Puck Line'),(200111,'NJ Devils @ DAL Stars','Tomorrow 20:07','Game Totals')])
add('Basketball','NBA/NBA',[(536203,'MIN Timberwolves @ CLE Cavaliers','Today 23:00','Money Line'),(536204,'IND Pacers @ MIL Bucks','Tomorrow 00:00','Money Line'),(536206,'MEM Grizzlies @ UTA Jazz','Tomorrow 01:00','Money Line'),(536199,'WAS Wizards @ CHA Hornets','Today 23:00','Money Line'),(536200,'DAL Mavericks @ MIA Heat','Today 23:30','Pointspread'),(536201,'ATL Hawks @ HOU Rockets','Tomorrow 00:30','Money Line'),(536205,'PHX Suns @ OKC Thunder','Tomorrow 00:00','Money Line'),(536202,'GS Warriors @ DEN Nuggets','Tomorrow 02:00','Money Line')])
add('Rugby League','All_Rugby_League/All_Events',[(2695857,'State of Origin 2027','27 May 2027 06:00','Win Tournament'),(2801554,'Super League 2027','02 Oct 2027 13:00','Grand Final Winner'),(2801600,'NRL 2027','03 Oct 2027 04:30','Grand Final Winner')])
for r in rows:
 if r['event_id']=='690271':r['flags'].append('OLBG explicitly displayed Expired')
 if r['sport']=='Greyhounds':r['flags'].append('Race label and displayed time differ; no timezone inferred')
 if r['sport'] in ('Cricket','Ice Hockey'):r['flags'].append('Overview and sport page display different local times')
 if r['event_id']=='160795':
  r['official_source']='https://www.mlb.com/schedule/2026-10-26';r['official_fact']='MLB lists MIL at TB on October 26, 2026 at 8:00 PM ET (World Series).'
  r['start_utc']='2026-10-27T00:00:00Z';r['flags'].remove('Absolute start and eligibility not confirmed');r['flags'].append('Schedule matched; live OLBG eligibility still unconfirmed')
 if r['event_id']=='914':
  r['official_source']='https://www.formula1.com/en/racing/2026/mexico';r['official_fact']='Official event page lists November 1 race, 71 laps, circuit length 4.304 km and race distance 305.354 km. Timezone not resolved.'
 if r['event_id'] in ('188852','188854','188868','188872','188835'):
  r['official_source']='https://www.icc-cricket.com/fixtures-results';r['official_fact']='ICC upcoming fixtures list contains these opponents and the format. Absolute date/time not established from the extracted listing.'
Path('data/research.json').write_text(json.dumps(dict(as_of='2026-10-26',complete=False,sports=sports,events=rows),indent=2)+'\n')
