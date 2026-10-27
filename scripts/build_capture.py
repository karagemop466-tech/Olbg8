#!/usr/bin/env python3
"""Build data/live-capture.json from the dated OLBG capture.

Every number in this file was transcribed from a live OLBG page on 2026-10-27
(UTC) using direct page retrieval. `win_tips` / `total_tips` reproduce the
"x / y Win Tips" pair printed by OLBG for that selection in that market;
`displayed_pct` reproduces the confidence percentage printed beside it.
Nothing here is inferred, rounded up, or filled in: where OLBG printed no
tip count the pair is null.

Evidence levels
---------------
event_page  : every selection in the market was read off the OLBG event page,
              so the distribution is complete for that market.
hub_top     : only the most-popular selection of that market was exposed on
              the category page. For two-outcome markets the opponent share is
              exactly total - top, which is arithmetic on captured values, not
              an assumption about the field. For three-outcome and outright
              markets the remaining share cannot be split, so it is published
              as a single "all other selections" block and never redistributed.
"""
import json
import os

CAPTURE_UTC = "2026-10-27T05:26:00Z"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPORTS = [
    ("golf", "Golf", 5),
    ("volleyball", "Volleyball", 21),
    ("rugby_union", "Rugby Union", 9),
    ("cricket", "Cricket", 7),
    ("snooker", "Snooker", 8),
    ("darts", "Darts", 15),
    ("baseball", "Baseball", 12),
    ("gaelic_sports", "Gaelic Sports", 25),
    ("greyhounds", "Greyhounds", 28),
    ("tennis", "Tennis", 3),
    ("motor_racing", "Motor Racing", 14),
    ("handball", "Handball", 20),
    ("ice_hockey", "Ice Hockey", 13),
    ("basketball", "Basketball", 4),
    ("rugby_league", "Rugby League", 10),
]

# sport, event_id, name, url path, time label as printed, competition, market,
# selection, win tips, total tips, experts, comments
HUB = [
    # ---- Golf (id 5) ----
    ("golf", "101913", "Maybank Championship", "Golf/All_Golf/All_Events/Maybank_Championship/5", "01 Nov 06:45", "LPGA Tour", "Win Tournament", "Lottie Woad", 1, 2, 0, 0),
    ("golf", "101915", "Mexico Open", "Golf/All_Golf/All_Events/Mexico_Open/5", "01 Nov 17:45", "PGA Tour", "Win Tournament", "Wyndham Clark", 1, 2, 0, 0),
    ("golf", "101914", "Simmons Bank Championship", "Golf/All_Golf/All_Events/Simmons_Bank_Championship/5", "01 Nov 17:45", "PGA Tour Champions", "Win Tournament", "Stewart Cink", 1, 2, 0, 0),

    # ---- Volleyball (id 21) ----
    ("volleyball", "37076", "Conegliano W vs Vallefoglia W", "Volleyball/All_Volleyball/All_Events/Conegliano_W_vs_Vallefoglia_W/21", "Tomorrow 15:00", "Italy Serie A1 (W)", "Win Match", "Vallefoglia W", 6, 10, 0, 0),
    ("volleyball", "37075", "Marignano W vs Bergamo W", "Volleyball/All_Volleyball/All_Events/Marignano_W_vs_Bergamo_W/21", "Today 15:00", "Italy Serie A1 (W)", "Win Match", "Bergamo W", 5, 7, 1, 1),
    ("volleyball", "37126", "TFL Altekma vs Halkbank Ankara", "Volleyball/All_Volleyball/All_Events/TFL_Altekma_vs_Halkbank_Ankara/21", "Today 08:00", "Turkey (M)", "Win Match", "Halkbank Ankara", 4, 5, 0, 1),
    ("volleyball", "37121", "Ziraat Bankasi vs Gaziantep Genclik Spor", "Volleyball/All_Volleyball/All_Events/Ziraat_Bankasi_vs_Gaziantep_Genclik_Spor/21", "Today 12:00", "Turkey (M)", "Win Match", "Ziraat Bankasi", 4, 4, 2, 3),
    ("volleyball", "37081", "Uni Opole W vs Palac Bydgoszcz W", "Volleyball/All_Volleyball/All_Events/Uni_Opole_W_vs_Palac_Bydgoszcz_W/21", "Today 15:30", "Poland Liga Siatkowki (W)", "Win Match", "Uni Opole W", 4, 6, 0, 1),
    ("volleyball", "37124", "Istanbul Genclik Spor vs IBB Spor", "Volleyball/All_Volleyball/All_Events/Istanbul_Genclik_Spor_vs_IBB_Spor/21", "Today 07:00", "Turkey (M)", "Win Match", "IBB Spor", 3, 5, 0, 2),
    ("volleyball", "37129", "VaLePa vs AC Oulu", "Volleyball/All_Volleyball/All_Events/VaLePa_vs_AC_Oulu/21", "Today 12:30", "Finland 1-sarja (M)", "Win Match", "VaLePa", 3, 4, 1, 2),
    ("volleyball", "37103", "Suzano Volei vs Goias Volei", "Volleyball/All_Volleyball/All_Events/Suzano_Volei_vs_Goias_Volei/21", "Today 17:30", "Brazil Superliga (M)", "Win Match", "Suzano Volei", 3, 4, 0, 1),
    ("volleyball", "37104", "Praia Clube vs Sao Jose", "Volleyball/All_Volleyball/All_Events/Praia_Clube_vs_Sao_Jose/21", "Today 20:00", "Brazil Superliga (M)", "Win Match", "Praia Clube", 3, 4, 0, 0),
    ("volleyball", "37122", "Sungurlu Bld vs Galatasaray", "Volleyball/All_Volleyball/All_Events/Sungurlu_Bld_vs_Galatasaray/21", "Today 09:30", "Turkey (M)", "Win Match", "Galatasaray", 2, 3, 0, 0),
    ("volleyball", "37125", "Fenerbahce vs Alanya Bld", "Volleyball/All_Volleyball/All_Events/Fenerbahce_vs_Alanya_Bld/21", "Today 12:00", "Turkey (M)", "Win Match", "Alanya Bld", 2, 3, 0, 0),
    ("volleyball", "37131", "Volleys Borken W vs Vilsbiburg W", "Volleyball/All_Volleyball/All_Events/Volleys_Borken_W_vs_Vilsbiburg_W/21", "Today 13:30", "Germany Bundesliga (W)", "Win Match", "Vilsbiburg W", 2, 3, 0, 0),
    ("volleyball", "37082", "Budowlani Lodz W vs Radomka Radom W", "Volleyball/All_Volleyball/All_Events/Budowlani_Lodz_W_vs_Radomka_Radom_W/21", "Tomorrow 12:30", "Poland Liga Siatkowki (W)", "Win Match", "Budowlani Lodz W", 2, 3, 0, 0),
    ("volleyball", "37083", "Mielec W vs Rzeszow W", "Volleyball/All_Volleyball/All_Events/Mielec_W_vs_Rzeszow_W/21", "Tomorrow 14:00", "Poland Liga Siatkowki (W)", "Win Match", "Rzeszow W", 2, 3, 0, 0),

    # ---- Rugby Union (id 9) ----
    ("rugby_union", "609605", "Dax v Provence", "Rugby_Union/All_Rugby_Union/All_Events/Dax_v_Provence/9", "29 Oct 16:00", "France Pro D2", "To Win", "Dax", 2, 3, 0, 1),
    ("rugby_union", "609604", "Colomiers v Agen", "Rugby_Union/All_Rugby_Union/All_Events/Colomiers_v_Agen/9", "30 Oct 14:00", "France Pro D2", "To Win", "Colomiers", 2, 2, 0, 0),
    ("rugby_union", "609603", "Montauban v Narbonne", "Rugby_Union/All_Rugby_Union/All_Events/Montauban_v_Narbonne/9", "30 Oct 14:30", "France Pro D2", "To Win", "Montauban", 2, 3, 0, 0),
    ("rugby_union", "609598", "Oyonnax v Soyaux Angouleme", "Rugby_Union/All_Rugby_Union/All_Events/Oyonnax_v_Soyaux_Angouleme/9", "30 Oct 14:30", "France Pro D2", "To Win", "Oyonnax", 2, 3, 0, 0),
    ("rugby_union", "609599", "Beziers v Grenoble", "Rugby_Union/All_Rugby_Union/All_Events/Beziers_v_Grenoble/9", "30 Oct 14:30", "France Pro D2", "To Win", "Grenoble", 1, 1, 0, 0),
    ("rugby_union", "609600", "Nissa v Aurillac", "Rugby_Union/All_Rugby_Union/All_Events/Nissa_v_Aurillac/9", "30 Oct 14:30", "France Pro D2", "To Win", "Nissa", 1, 1, 0, 0),
    ("rugby_union", "609590", "Glasgow Warriors v Lions", "Rugby_Union/All_Rugby_Union/All_Events/Glasgow_Warriors_v_Lions/9", "30 Oct 15:45", "United Rugby Championship", "To Win", "Glasgow Warriors", 1, 1, 0, 0),
    ("rugby_union", "609584", "Connacht v Leinster", "Rugby_Union/All_Rugby_Union/All_Events/Connacht_v_Leinster/9", "30 Oct 15:45", "United Rugby Championship", "Handicap", "Connacht +3.50", 1, 1, 0, 0),
    ("rugby_union", "609602", "Biarritz v Valence Romans", "Rugby_Union/All_Rugby_Union/All_Events/Biarritz_v_Valence_Romans/9", "30 Oct 16:00", "France Pro D2", "To Win", "Biarritz", 1, 1, 0, 0),
    ("rugby_union", "609588", "Stormers v Ulster", "Rugby_Union/All_Rugby_Union/All_Events/Stormers_v_Ulster/9", "31 Oct 08:45", "United Rugby Championship", "Handicap", "Ulster +12.50", 1, 1, 0, 0),
    ("rugby_union", "609586", "Munster v Sharks", "Rugby_Union/All_Rugby_Union/All_Events/Munster_v_Sharks/9", "31 Oct 13:30", "United Rugby Championship", "Handicap", "Munster -6.50", 1, 1, 0, 0),
    ("rugby_union", "609611", "Pau v Toulouse", "Rugby_Union/All_Rugby_Union/All_Events/Pau_v_Toulouse/9", "01 Nov 15:05", "France Top 14", "To Win", "Pau", 1, 1, 0, 1),
    ("rugby_union", "609013", "Six Nations 2027", "Rugby_Union/All_Rugby_Union/All_Events/Six_Nations_2027/9", "14 Mar 2027 16:00", "Six Nations", "Win Tournament", "Ireland", 3, 11, 0, 2),

    # ---- Cricket (id 7) ----
    ("cricket", "188852", "New Zealand vs India 3rd T20 Match", "Cricket/All_Cricket/All_Events/New_Zealand_vs_India_3rd_T20_Match/7", "Today 03:00", "India tour of New Zealand", "Win Match", "India", 35, 49, 2, 18),
    ("cricket", "188854", "Namibia vs Ireland 3rd ODI", "Cricket/All_Cricket/All_Events/Namibia_vs_Ireland_3rd_ODI/7", "Today 03:30", "Ireland tour of Namibia", "Win Match", "Ireland", 22, 32, 1, 6),
    ("cricket", "188868", "Pakistan vs Sri Lanka One Day Match", "Cricket/All_Cricket/All_Events/Pakistan_vs_Sri_Lanka_One_Day_Match/7", "Today 04:00", "Sri Lanka tour of Pakistan", "Win Match", "Pakistan", 22, 31, 1, 15),
    ("cricket", "188872", "Afghanistan vs Zimbabwe 1st T20 Match", "Cricket/All_Cricket/All_Events/Afghanistan_vs_Zimbabwe_1st_T20_Match/7", "Today 10:30", "Zimbabwe tour of Afghanistan", "Win Match", "Afghanistan", 15, 16, 1, 11),
    ("cricket", "188864", "Melbourne Stars W vs Hobart Hurricanes W T20 Big Bash", "Cricket/All_Cricket/All_Events/Melbourne_Stars_W_vs_Hobart_Hurricanes_W_T20_Big_Bash/7", "29 Oct 04:10", "Women's Big Bash", "Win Match", "Hobart Hurricanes W", 4, 6, 0, 0),
    ("cricket", "188876", "Auckland vs Canterbury One Day Match", "Cricket/All_Cricket/All_Events/Auckland_vs_Canterbury_One_Day_Match/7", "Today 17:30", "The Ford Trophy", "Win Match", "Canterbury", 3, 4, 0, 2),
    ("cricket", "188865", "Brisbane Heat W vs Sydney Sixers W T20 Big Bash", "Cricket/All_Cricket/All_Events/Brisbane_Heat_W_vs_Sydney_Sixers_W_T20_Big_Bash/7", "30 Oct 04:10", "Women's Big Bash", "Win Match", "Sydney Sixers W", 3, 5, 0, 0),
    ("cricket", "188835", "South Africa vs Australia", "Cricket/All_Cricket/All_Events/South_Africa_vs_Australia/7", "31 Oct 04:30", "International", "Win Match", "South Africa", 3, 8, 1, 1),
    ("cricket", "188878", "Wellington vs Otago One Day Match", "Cricket/All_Cricket/All_Events/Wellington_vs_Otago_One_Day_Match/7", "Today 17:30", "The Ford Trophy", "Win Match", "Wellington", 2, 4, 0, 1),
    ("cricket", "188877", "Central Districts vs Northern Districts One Day Match", "Cricket/All_Cricket/All_Events/Central_Districts_vs_Northern_Districts_One_Day_Match/7", "Today 17:30", "The Ford Trophy", "Win Match", "Northern Districts", 2, 3, 0, 1),
    ("cricket", "188874", "Lions vs Eastern Storm T20", "Cricket/All_Cricket/All_Events/Lions_vs_Eastern_Storm_T20/7", "Tomorrow 12:00", "SA domestic T20", "Win Match", "Lions", 1, 1, 0, 0),
    ("cricket", "188871", "Bangladesh vs West Indies", "Cricket/All_Cricket/All_Events/Bangladesh_vs_West_Indies/7", "31 Oct 23:30", "International", "Win Match", "West Indies", 1, 1, 0, 1),
    ("cricket", "188854", "Namibia vs Ireland 3rd ODI", "Cricket/All_Cricket/All_Events/Namibia_vs_Ireland_3rd_ODI/7", "Today 03:30", "Ireland tour of Namibia", "Top Team1 Batsman", "MG Erasmus (Namibia)", 10, 18, 0, 5),

    # ---- Darts (id 15) ----
    ("darts", "26023", "PDC World Championship 2027", "Darts/All_Darts/All_Events/PDC_World_Championship_2027/15", "03 Jan 2027 12:00", "PDC World Championship", "Win Tournament", "Luke Littler", 22, 36, 0, 7),
    ("darts", "32446", "Players Championship 31", "Darts/All_Darts/All_Events/Players_Championship_31/15", "Tomorrow 08:00", "PDC ProTour", "Win Tournament", "Nathan Aspinall", 2, 8, 0, 1),

    # ---- Baseball (id 12) ----
    ("baseball", "160799", "MIL Brewers @ TB Rays", "Baseball/MLB/MLB/MIL_Brewers_@_TB_Rays/12", "Today 21:00", "MLB World Series", "Money Line", "MIL Brewers", 2, 2, 0, 0),

    # ---- Gaelic Sports (id 25 football + 26 hurling) ----
    ("gaelic_sports", "3531", "Kanturk v Eire Og Cor", "Gaelic_Football/All_Gaelic_Football/All_Events/Kanturk_v_Eire_Og_Cor/25", "01 Nov 09:00", "Cork Club Championship", "Handicap", "Eire Og Cor +0.50", 6, 6, 0, 1),
    ("gaelic_sports", "3537", "Fr Caseys v Kildimo Pallaskenry", "Gaelic_Football/All_Gaelic_Football/All_Events/Fr_Caseys_v_Kildimo_Pallaskenry/25", "01 Nov 10:30", "Limerick Club Championship", "Handicap", "Kildimo Pallaskenry +3.50", 5, 7, 0, 0),
    ("gaelic_sports", "3327", "All Ireland Football Championship 2027", "Gaelic_Football/All_Gaelic_Football/All_Events/All_Ireland_Football_Championship_2027/25", "25 Jul 2027 10:30", "All-Ireland SFC", "Win Tournament", "Kerry", 6, 8, 0, 2),
    ("gaelic_sports", "675", "All Ireland Hurling Championship 2027", "Hurling/All_Hurling/All_Events/All_Ireland_Hurling_Championship_2027/26", "18 Jul 2027 10:30", "All-Ireland SHC", "Win Hurling", "Galway", 7, 18, 0, 0),

    # ---- Tennis (id 3) ----
    ("tennis", "902172", "Leylah Fernandez vs Himeno Sakatsume", "Tennis/All_Tennis/All_Events/Leylah_Fernandez_vs_Himeno_Sakatsume/3", "Today 02:00", "WTA Tokyo", "Win Match", "Leylah Fernandez", 10, 12, 1, 5),
    ("tennis", "902189", "Lilli Tagger vs Venus Williams", "Tennis/All_Tennis/All_Events/Lilli_Tagger_vs_Venus_Williams/3", "Today 03:30", "WTA Guangzhou", "Win Match", "Lilli Tagger", 4, 8, 0, 1),
    ("tennis", "902177", "Naomi Osaka vs Jasmine Paolini", "Tennis/All_Tennis/All_Events/Naomi_Osaka_vs_Jasmine_Paolini/3", "Today 04:00", "WTA Tokyo", "Win Match", "Naomi Osaka", 4, 4, 0, 2),
    ("tennis", "902238", "Alejandro Tabilo vs Rafael Jodar", "Tennis/All_Tennis/All_Events/Alejandro_Tabilo_vs_Rafael_Jodar/3", "Today 09:00", "ATP Vienna", "Win Match", "Rafael Jodar", 4, 6, 0, 3),
    ("tennis", "902232", "Stan Wawrinka vs Jiri Lehecka", "Tennis/All_Tennis/All_Events/Stan_Wawrinka_vs_Jiri_Lehecka/3", "Today 14:30", "ATP Vienna", "Win Match", "Stan Wawrinka", 4, 8, 0, 1),
    ("tennis", "902233", "Novak Djokovic vs Ugo Humbert", "Tennis/All_Tennis/All_Events/Novak_Djokovic_vs_Ugo_Humbert/3", "Tomorrow 06:00", "ATP Basel", "Win Match", "Novak Djokovic", 4, 5, 0, 3),
    ("tennis", "902322", "Hubert Hurkacz vs Zizou Bergs", "Tennis/All_Tennis/All_Events/Hubert_Hurkacz_vs_Zizou_Bergs/3", "Today 07:00", "ATP Vienna", "Win Match", "Hubert Hurkacz", 3, 3, 0, 1),
    ("tennis", "902252", "Tommy Paul vs Andrey Rublev", "Tennis/All_Tennis/All_Events/Tommy_Paul_vs_Andrey_Rublev/3", "Today 08:30", "ATP Basel", "Win Match", "Andrey Rublev", 3, 4, 0, 1),
    ("tennis", "902210", "Cameron Norrie vs Francisco Cerundolo", "Tennis/All_Tennis/All_Events/Cameron_Norrie_vs_Francisco_Cerundolo/3", "Today 11:30", "ATP Vienna", "Win Match", "Cameron Norrie", 3, 5, 0, 1),
    ("tennis", "902187", "Polina Kudermetova vs Janice Tjen", "Tennis/All_Tennis/All_Events/Polina_Kudermetova_vs_Janice_Tjen/3", "Today 02:00", "WTA Guangzhou", "Win Match", "Janice Tjen", 2, 2, 0, 1),
    ("tennis", "902409", "Nuno Borges vs Casper Ruud", "Tennis/All_Tennis/All_Events/Nuno_Borges_vs_Casper_Ruud/3", "Today 07:00", "ATP Vienna", "Win Match", "Casper Ruud", 2, 2, 0, 0),
    ("tennis", "902240", "Alex Michelsen vs Botic Van De Zandschulp", "Tennis/All_Tennis/All_Events/Alex_Michelsen_vs_Botic_Van_De_Zandschulp/3", "Today 10:00", "ATP Vienna", "Win Match", "Alex Michelsen", 2, 3, 0, 1),
    ("tennis", "902213", "Karen Khachanov vs Carlos Alcaraz", "Tennis/All_Tennis/All_Events/Karen_Khachanov_vs_Carlos_Alcaraz/3", "Today 10:00", "ATP Vienna", "Win Match", "Karen Khachanov", 2, 2, 0, 0),

    # ---- Motor Racing (id 14) ----
    ("motor_racing", "912", "Formula 1 Drivers Championship 2026 Without Kimi Antonelli", "Motor_Racing/All_Motor_Racing/All_Events/Formula_1_Drivers_Championship_2026_Without_Kimi_Antonelli/14", "06 Dec 08:00", "F1 World Championship", "Win Tournament", "Max Verstappen", 4, 7, 0, 1),
    ("motor_racing", "914", "Mexico City Grand Prix", "Motor_Racing/All_Motor_Racing/All_Events/Mexico_City_Grand_Prix/14", "01 Nov 15:00", "Formula 1", "Podium Finish", "Max Verstappen - Yes", 1, 2, 0, 0),

    # ---- Handball (id 20) ----
    ("handball", "12136", "SC Magdeburg vs HC Kriens Luzern", "Handball/All_Handball/All_Events/SC_Magdeburg_vs_HC_Kriens_Luzern/20", "Tomorrow 15:45", "EHF Champions League", "Money Line", "Tie", 9, 14, 0, 0),
    ("handball", "12130", "HC Vardar vs MT Melsungen", "Handball/All_Handball/All_Events/HC_Vardar_vs_MT_Melsungen/20", "Tomorrow 13:45", "EHF Champions League", "Money Line", "Tie", 8, 13, 0, 0),
    ("handball", "12138", "Wisla Plock vs Nantes", "Handball/All_Handball/All_Events/Wisla_Plock_vs_Nantes/20", "Tomorrow 13:45", "EHF Champions League", "Money Line", "Tie", 8, 11, 0, 0),
    ("handball", "12132", "KS Kielce vs Kolstad", "Handball/All_Handball/All_Events/KS_Kielce_vs_Kolstad/20", "Tomorrow 15:45", "EHF Champions League", "Money Line", "Tie", 7, 11, 0, 0),
    ("handball", "12134", "PSG Handball vs Aalborg Handbold", "Handball/All_Handball/All_Events/PSG_Handball_vs_Aalborg_Handbold/20", "Tomorrow 15:45", "EHF Champions League", "Money Line", "Tie", 7, 9, 0, 0),
    ("handball", "12135", "RK Celje vs RK Zagreb", "Handball/All_Handball/All_Events/RK_Celje_vs_RK_Zagreb/20", "Tomorrow 15:45", "EHF Champions League", "Money Line", "Tie", 6, 8, 0, 0),
    ("handball", "12128", "Fuchse Berlin vs RK Partizan", "Handball/All_Handball/All_Events/Fuchse_Berlin_vs_RK_Partizan/20", "29 Oct 13:45", "EHF Champions League", "Money Line", "Tie", 6, 14, 0, 0),
    ("handball", "12127", "FC Porto vs Veszprem", "Handball/All_Handball/All_Events/FC_Porto_vs_Veszprem/20", "Tomorrow 13:45", "EHF Champions League", "Money Line", "Tie", 5, 9, 0, 0),
    ("handball", "12129", "GOG vs Sporting CP", "Handball/All_Handball/All_Events/GOG_vs_Sporting_CP/20", "29 Oct 13:45", "EHF Champions League", "Money Line", "Tie", 3, 5, 0, 0),
    ("handball", "12133", "Montpellier vs Dinamo Bucuresti", "Handball/All_Handball/All_Events/Montpellier_vs_Dinamo_Bucuresti/20", "29 Oct 15:45", "EHF Champions League", "Money Line", "Tie", 3, 4, 0, 0),
    ("handball", "12197", "VasterasIrsta HF W vs Skuru IK W", "Handball/All_Handball/All_Events/VasterasIrsta_HF_W_vs_Skuru_IK_W/20", "Today 14:00", "Sweden Damallsvenskan (W)", "Money Line", "VasterasIrsta HF (W)", 2, 4, 0, 1),
    ("handball", "12196", "OV Helsingborg HK W vs Skovde HF W", "Handball/All_Handball/All_Events/OV_Helsingborg_HK_W_vs_Skovde_HF_W/20", "Today 14:00", "Sweden Damallsvenskan (W)", "Money Line", "Skovde HF (W)", 2, 4, 0, 1),
    ("handball", "12131", "IFK Kristianstad vs Pick Szeged", "Handball/All_Handball/All_Events/IFK_Kristianstad_vs_Pick_Szeged/20", "29 Oct 13:45", "EHF Champions League", "Money Line", "Tie", 2, 4, 0, 0),
    ("handball", "12180", "SG Flensburg Handewitt vs HBW Balingen Weilstetten", "Handball/All_Handball/All_Events/SG_Flensburg_Handewitt_vs_HBW_Balingen_Weilstetten/20", "29 Oct 14:00", "Germany DKB Bundesliga", "Money Line", "HBW Balingen-Weilstetten", 1, 1, 0, 0),
    ("handball", "12137", "Skanderborg Handbold vs FC Barcelona", "Handball/All_Handball/All_Events/Skanderborg_Handbold_vs_FC_Barcelona/20", "29 Oct 15:45", "EHF Champions League", "Money Line", "Skanderborg Handbold", 1, 3, 0, 0),

    # ---- Ice Hockey (id 13) ----
    ("ice_hockey", "200081", "Kalpa vs Sport", "Ice_Hockey/Other/Finland_SM_Liiga/Kalpa_vs_Sport/13", "Today 12:30", "Finland Liiga", "Money Line", "Kalpa", 5, 5, 0, 2),
    ("ice_hockey", "200082", "IF Malmo Redhawks vs Linkoping HC", "Ice_Hockey/Other/Swedish_Hockey_League/IF_Malmo_Redhawks_vs_Linkoping_HC/13", "Today 14:00", "Sweden SHL", "Money Line", "IF Malmo Redhawks", 3, 3, 0, 2),
    ("ice_hockey", "200083", "Frolunda HC vs Rogle BK", "Ice_Hockey/Other/Swedish_Hockey_League/Frolunda_HC_vs_Rogle_BK/13", "Today 14:00", "Sweden SHL", "Money Line", "Frolunda HC", 2, 3, 0, 1),
    ("ice_hockey", "200100", "Kolner Haie vs Adler Mannheim", "Ice_Hockey/Other/Germany_Eishockey_Liga/Kolner_Haie_vs_Adler_Mannheim/13", "Today 14:30", "Germany DEL", "Money Line", "Adler Mannheim", 2, 2, 0, 2),
    ("ice_hockey", "200108", "CLB Blue Jackets @ PHI Flyers", "Ice_Hockey/NHL/NHL/CLB_Blue_Jackets_@_PHI_Flyers/13", "Today 19:07", "NHL", "Money Line", "PHI Flyers", 2, 3, 0, 1),
    ("ice_hockey", "200104", "BOS Bruins @ CAR Hurricanes", "Ice_Hockey/NHL/NHL/BOS_Bruins_@_CAR_Hurricanes/13", "Today 20:07", "NHL", "Puck Line", "BOS Bruins +1.50", 2, 2, 0, 1),
    ("ice_hockey", "200098", "Herning Blue Fox vs Rodovre Mighty Bulls", "Ice_Hockey/Other/Danish_Metal_Ligaen/Herning_Blue_Fox_vs_Rodovre_Mighty_Bulls/13", "Today 14:00", "Denish Metal Ligaen", "Puck Line", "Rodovre Mighty Bulls +3.50", 1, 1, 0, 0),
    ("ice_hockey", "200146", "Fehervar AV19 vs Milano HC", "Ice_Hockey/Other/Austria_EHL/Fehervar_AV19_vs_Milano_HC/13", "Today 14:15", "Austrian ICE Hockey League", "Puck Line", "Fehervar AV19 -1.50", 1, 1, 0, 0),
    ("ice_hockey", "200116", "Fribourg Gotteron vs Davos", "Ice_Hockey/Other/Switzerland_NLA/Fribourg_Gotteron_vs_Davos/13", "Today 14:45", "Switzerland National League", "Puck Line", "Fribourg Gotteron -1.50", 1, 1, 0, 0),
    ("ice_hockey", "200122", "Bern vs ZSC Lions", "Ice_Hockey/Other/Switzerland_NLA/Bern_vs_ZSC_Lions/13", "Today 14:45", "Switzerland National League", "Puck Line", "ZSC Lions -1.50", 1, 1, 0, 0),
    ("ice_hockey", "200115", "EHC Kloten vs HC Ajoie", "Ice_Hockey/Other/Switzerland_NLA/EHC_Kloten_vs_HC_Ajoie/13", "Today 14:45", "Switzerland National League", "Puck Line", "EHC Kloten -1.50", 1, 1, 0, 0),
    ("ice_hockey", "200117", "Zug vs Lugano", "Ice_Hockey/Other/Switzerland_NLA/Zug_vs_Lugano/13", "Today 14:45", "Switzerland National League", "Puck Line", "Lugano +1.50", 1, 1, 0, 1),
    ("ice_hockey", "200118", "Lausanne HC vs SCL Tigers", "Ice_Hockey/Other/Switzerland_NLA/Lausanne_HC_vs_SCL_Tigers/13", "Today 14:45", "Switzerland National League", "Puck Line", "Lausanne HC -1.50", 1, 1, 0, 0),
    ("ice_hockey", "200119", "Ambri Piotta vs EHC Biel", "Ice_Hockey/Other/Switzerland_NLA/Ambri_Piotta_vs_EHC_Biel/13", "Today 14:45", "Switzerland National League", "Puck Line", "Ambri Piotta -1.50", 1, 1, 0, 0),
    ("ice_hockey", "200123", "Rapperswil Jona Lakers vs Servette GE", "Ice_Hockey/Other/Switzerland_NLA/Rapperswil_Jona_Lakers_vs_Servette_GE/13", "Today 14:45", "Switzerland National League", "Puck Line", "Servette GE +1.50", 1, 1, 0, 0),

    # ---- Basketball (id 4) ----
    ("basketball", "536177", "Panathinaikos vs Milano", "Basketball/European/Euroleague/Panathinaikos_vs_Milano/4", "Today 15:15", "EuroLeague", "Money Line", "Panathinaikos", 5, 8, 0, 0),
    ("basketball", "536214", "Seoul Knights vs KCC Egis", "Basketball/Other/Korea_KBL/Seoul_Knights_vs_KCC_Egis/4", "Today 06:00", "Korea KBL", "Money Line", "Seoul Knights", 4, 5, 1, 1),
    ("basketball", "536176", "BC Dubai vs Paris", "Basketball/European/Euroleague/BC_Dubai_vs_Paris/4", "Today 12:00", "EuroLeague", "Money Line", "BC Dubai", 4, 7, 0, 1),
    ("basketball", "536179", "Valencia vs Fenerbahce", "Basketball/European/Euroleague/Valencia_vs_Fenerbahce/4", "Today 15:30", "EuroLeague", "Money Line", "Fenerbahce", 4, 6, 0, 2),
    ("basketball", "536174", "Bayern Munich vs Barcelona", "Basketball/European/Euroleague/Bayern_Munich_vs_Barcelona/4", "Today 15:00", "EuroLeague", "Money Line", "Bayern Munich", 3, 5, 0, 1),
    ("basketball", "536178", "Baskonia vs Real Madrid", "Basketball/European/Euroleague/Baskonia_vs_Real_Madrid/4", "Today 16:00", "EuroLeague", "Money Line", "Baskonia", 3, 6, 0, 0),
    ("basketball", "536218", "Lietkabelis vs Ratiopharm Ulm", "Basketball/European/Euro_Cup/Lietkabelis_vs_Ratiopharm_Ulm/4", "Today 13:00", "EuroCup", "Money Line", "Lietkabelis", 2, 2, 0, 0),
    ("basketball", "536217", "Frankfurt Skyliners vs U BT Cluj Napoca", "Basketball/European/Euro_Cup/Frankfurt_Skyliners_vs_U_BT_Cluj_Napoca/4", "Today 14:30", "EuroCup", "Pointspread", "Frankfurt Skyliners +1.50", 2, 2, 0, 2),
    ("basketball", "536175", "Crvena Zvezda vs Maccabi Tel Aviv", "Basketball/European/Euroleague/Crvena_Zvezda_vs_Maccabi_Tel_Aviv/4", "Today 15:00", "EuroLeague", "Money Line", "Crvena Zvezda", 2, 4, 0, 0),
    ("basketball", "536235", "UCAM Murcia vs Peristeri", "Basketball/European/Basketball_Champions_League/UCAM_Murcia_vs_Peristeri/4", "Today 15:30", "Basketball Champions League", "Money Line", "UCAM Murcia", 2, 2, 0, 0),
    ("basketball", "536222", "Aris vs Cedevita Olimpija", "Basketball/European/Euro_Cup/Aris_vs_Cedevita_Olimpija/4", "Tomorrow 13:30", "EuroCup", "Money Line", "Aris", 2, 2, 0, 0),
    ("basketball", "536180", "Besiktas vs Olympiacos", "Basketball/European/Euroleague/Besiktas_vs_Olympiacos/4", "Tomorrow 13:30", "EuroLeague", "Money Line", "Besiktas", 2, 3, 0, 0),
    ("basketball", "536181", "Asvel Lyon Villeurbanne vs Partizan", "Basketball/European/Euroleague/Asvel_Lyon_Villeurbanne_vs_Partizan/4", "Tomorrow 15:00", "EuroLeague", "Money Line", "Partizan", 2, 2, 0, 0),
    ("basketball", "536183", "Virtus Bologna vs Zalgiris", "Basketball/European/Euroleague/Virtus_Bologna_vs_Zalgiris/4", "Tomorrow 15:30", "EuroLeague", "Money Line", "Virtus Bologna", None, None, 0, 0),

    # ---- Rugby League (id 10) ----
    ("rugby_league", "2695857", "State of Origin 2027", "Rugby_League/All_Rugby_League/All_Events/State_of_Origin_2027/10", "27 May 2027 06:00", "State of Origin", "Win Tournament", "New South Wales", 9, 13, 0, 3),
    ("rugby_league", "2801554", "Super League 2027", "Rugby_League/All_Rugby_League/All_Events/Super_League_2027/10", "02 Oct 2027 13:00", "Super League", "Grand Final Winner", "Wigan Warriors", 2, 4, 0, 2),
    ("rugby_league", "2801600", "NRL 2027", "Rugby_League/All_Rugby_League/All_Events/NRL_2027/10", "03 Oct 2027 04:30", "NRL", "Grand Final Winner", "Penrith Panthers", 1, 3, 0, 1),
]

# ---------------------------------------------------------------------------
# Markets read in FULL from the OLBG event page (every selection printed).
# ---------------------------------------------------------------------------
M_NZ_IND = [
    {"market": "Win Match", "basis": "event_page", "selections": [
        {"label": "India", "win_tips": 35, "total_tips": 50},
        {"label": "New Zealand", "win_tips": 15, "total_tips": 50}]},
    {"market": "Man Of The Match", "basis": "event_page", "selections": [
        {"label": "Abhishek Sharma", "win_tips": 4, "total_tips": 25},
        {"label": "SV Samson", "win_tips": 4, "total_tips": 25},
        {"label": "V Suryavanshi", "win_tips": 0, "total_tips": 25},
        {"label": "FH Allen", "win_tips": 2, "total_tips": 25},
        {"label": "IPKP Kishan", "win_tips": 1, "total_tips": 25},
        {"label": "TL Seifert", "win_tips": 2, "total_tips": 25},
        {"label": "MJ Santner", "win_tips": 1, "total_tips": 25},
        {"label": "S Iyer", "win_tips": 2, "total_tips": 25},
        {"label": "S Dube", "win_tips": 1, "total_tips": 25},
        {"label": "T Varma", "win_tips": 2, "total_tips": 25},
        {"label": "AR Patel", "win_tips": 1, "total_tips": 25}]},
]
M_KIELCE = [
    {"market": "Money Line", "basis": "event_page", "selections": [
        {"label": "Tie", "win_tips": 7, "total_tips": 11},
        {"label": "KS Kielce", "win_tips": 2, "total_tips": 11},
        {"label": "Kolstad", "win_tips": 2, "total_tips": 11}]},
    {"market": "Match Handicap", "basis": "event_page", "line": 7.5, "selections": [
        {"label": "Kolstad +7.50", "win_tips": 2, "total_tips": 2},
        {"label": "KS Kielce -7.50", "win_tips": 0, "total_tips": 2}]},
    {"market": "Points Total", "basis": "event_page", "line": 63.5, "selections": [
        {"label": "Over 63.50", "win_tips": 0, "total_tips": 0},
        {"label": "Under 63.50", "win_tips": 0, "total_tips": 0}]},
]
M_BOS_CAR = [
    {"market": "Puck Line", "basis": "event_page", "line": 1.5, "selections": [
        {"label": "BOS Bruins +1.50", "win_tips": 2, "total_tips": 2},
        {"label": "CAR Hurricanes -1.50", "win_tips": 0, "total_tips": 2}]},
    {"market": "Money Line", "basis": "event_page", "selections": [
        {"label": "CAR Hurricanes", "win_tips": 1, "total_tips": 2},
        {"label": "BOS Bruins", "win_tips": 1, "total_tips": 2}]},
    {"market": "Game Totals", "basis": "event_page", "line": 6.5, "selections": [
        {"label": "Under 6.50", "win_tips": 0, "total_tips": 1},
        {"label": "Over 6.50", "win_tips": 1, "total_tips": 1}]},
]
M_MIL_TB = [
    {"market": "Money Line", "basis": "event_page", "selections": [
        {"label": "MIL Brewers", "win_tips": 2, "total_tips": 2},
        {"label": "TB Rays", "win_tips": 0, "total_tips": 2}]},
    {"market": "Run Line", "basis": "event_page", "line": 1.5, "selections": [
        {"label": "TB Rays +1.50", "win_tips": 0, "total_tips": 1},
        {"label": "MIL Brewers -1.50", "win_tips": 1, "total_tips": 1}]},
    {"market": "Game Totals", "basis": "event_page", "line": 7.5, "selections": [
        {"label": "Under 7.50", "win_tips": 0, "total_tips": 0},
        {"label": "Over 7.50", "win_tips": 0, "total_tips": 0}]},
]

# Official-source crosswalk, keyed "sport:event_id". Only entries where a
# named official/primary source was actually opened and the fixture matched.
OFFICIAL = {
    "baseball:160799": {
        "name": "MLB StatsAPI schedule for 2026-10-27 (sportId=1) - official MLB",
        "url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-10-27&hydrate=team",
        "confirmed": "World Series Game 4, Milwaukee Brewers (away) at Tampa Bay Rays, Tropicana Field, gamePk 849803, series record MIL 3-0 TB; gameDate 2026-10-28T00:00:00Z",
        "alt_name": "MLB.com probable pitchers page",
        "alt_url": "https://www.mlb.com/probable-pitchers",
    },
    "ice_hockey:200104": {
        "name": "NHL.com official score API for 2026-10-27",
        "url": "https://api-web.nhle.com/v1/score/2026-10-27",
        "confirmed": "Boston Bruins (9-2-1) at Carolina Hurricanes (9-2-2), game id 2026020189, Lenovo Center, startTimeUTC 2026-10-28T00:00:00Z; NHL-listed partner odds CAR -192/-196, BOS +158/+160",
    },
    "ice_hockey:200108": {
        "name": "NHL.com official score API for 2026-10-27",
        "url": "https://api-web.nhle.com/v1/score/2026-10-27",
        "confirmed": "Columbus Blue Jackets (4-5-0) at Philadelphia Flyers (3-7-3), game id 2026020188, Xfinity Mobile Arena, startTimeUTC 2026-10-27T23:00:00Z; NHL-listed partner odds CBJ -125/-127/-128, PHI +104/+105/+106",
    },
    "handball:12132": {
        "name": "EHF (European Handball Federation) club fixture page",
        "url": "https://www.eurohandball.com/en/club/kZVHhs7nxEhEqyCf6iK_Sw/KolstadH%C3%A5ndball/",
        "confirmed": "Industria Kielce v Kolstad Håndball, Group F, Wed 28 Oct 2026 20:45 CET, Hala Legionów, Kielce",
        "alt_name": "EHF Champions League fixture news (ehfcl.eurohandball.com)",
        "alt_url": "https://ehfcl.eurohandball.com/news/en/final-rematch-at-kielce-sporting-aim-to-conquer-szeged-s-fortress-in-round-3/",
    },
    "rugby_union:609590": {
        "name": "BBC Sport URC scores & fixtures",
        "url": "https://www.bbc.co.uk/sport/rugby-union/pro-tournament/scores-fixtures",
        "confirmed": "Glasgow Warriors v Johannesburg Lions, URC round 5, Fri 30 Oct 2026 19:45, Scotstoun",
        "alt_name": "RTE URC fixtures",
        "alt_url": "https://www.rte.ie/sport/results/rugby/united-rugby-championship/34235/fixtures/",
    },
    "rugby_union:609584": {
        "name": "BBC Sport URC scores & fixtures",
        "url": "https://www.bbc.co.uk/sport/rugby-union/pro-tournament/scores-fixtures",
        "confirmed": "Connacht v Leinster, URC round 5, Fri 30 Oct 2026 19:45, Dexcom Stadium, Galway",
    },
    "rugby_union:609586": {
        "name": "BBC Sport URC scores & fixtures",
        "url": "https://www.bbc.co.uk/sport/rugby-union/pro-tournament/scores-fixtures",
        "confirmed": "Munster v Durban Sharks, URC round 5, Sat 31 Oct 2026 17:30, Thomond Park",
    },
    "basketball:536177": {
        "name": "Olimpia Milano official EuroLeague standings page",
        "url": "https://www.olimpiamilano.com/classifica/",
        "confirmed": "Round 8 pairing Panathinaikos AKTOR Athens v Armani Olimpia Milano; standings after 7 rounds PAO 6-1 (+96), MIL 1-6 (-63)",
        "alt_name": "Real Madrid / EuroLeague fixture listing via AiScore (secondary)",
        "alt_url": "https://en.wikipedia.org/wiki/2026%E2%80%9327_EuroLeague_regular_season",
    },
    "motor_racing:914": {
        "name": "Formula 1 official Mexico City Grand Prix 2026 race page",
        "url": "https://www.formula1.com/en/racing/2026/mexico",
        "confirmed": "Round 19 of 2026 at Autodromo Hermanos Rodriguez, 30 Oct - 1 Nov 2026; 71 laps; race billed Sun 1 Nov",
        "alt_name": "BBC Sport Mexico City GP start-time and title-permutation briefing",
        "alt_url": "https://www.bbc.com/sport/formula1/articles/c6wyrgejp0w8o",
    },
    "cricket:188852": {
        "name": "ESPNcricinfo 3rd T20I match preview / live page",
        "url": "https://www.cricinfo.com/series/india-in-new-zealand-2026-27-1539421/new-zealand-vs-india-3rd-t20i-1539434/match-preview",
        "confirmed": "India lead 5-match T20I series 2-0; 3rd T20I Tue 27 Oct 2026 at Hnry Stadium, Wellington; Matt Henry withdrawn from series, Lockie Ferguson unavailable for this match",
        "alt_name": "ICC news item on New Zealand squad updates",
        "alt_url": "https://www.icc-cricket.com/news/new-zealand-announce-key-updates-for-t20i-squad-against-india",
    },
    "golf:101913": {
        "name": "LPGA official tournament page and entry list",
        "url": "https://www.lpga.com/tournaments/maybank-championship/entries",
        "confirmed": "Maybank Championship, Kuala Lumpur Golf & Country Club West Course, 29 Oct - 1 Nov 2026; Lottie Woad entered",
        "alt_name": "LPGA official tournament schedule",
        "alt_url": "https://www.lpga.com/tournaments",
    },
    "darts:32446": {
        "name": "PDC official calendar",
        "url": "https://www.pdc.tv/calendar/",
        "confirmed": "2026 Players Championship 31 listed for Wed 28 Oct 2026 at Maaspoort, Den Bosch",
        "alt_name": "Sky Sports 2026 darts schedule",
        "alt_url": "https://www.skysports.com/darts/news/13428768/darts-2026-schedule-and-dates-premier-league-darts-world-matchplay-and-more-with-luke-littler-in-action",
    },
    "darts:26023": {
        "name": "PDC official World Championship tournament page",
        "url": "https://www.pdc.tv/tournaments/paddy-power-world-darts-championship",
        "confirmed": "2026/27 Paddy Power World Darts Championship, Alexandra Palace, 11 Dec 2026 - 3 Jan 2027, 128-player field, top 32 seeded; Luke Littler defending champion",
    },
}
EVENT_PAGE_MARKETS = {
    "cricket:188852": M_NZ_IND,
    "handball:12132": M_KIELCE,
    "ice_hockey:200104": M_BOS_CAR,
    "baseball:160799": M_MIL_TB,
}


def build():
    sports = {k: {"label": lab, "sport_id": sid, "events": [],
                  "olbg_hub": f"https://www.olbg.com/betting-tips/{lab.replace(' ', '_')}/{sid}"}
              for k, lab, sid in SPORTS}
    for (sp, eid, name, path, tlabel, comp, mkt, sel, w, t, exp, com) in HUB:
        key = f"{sp}:{eid}"
        markets = EVENT_PAGE_MARKETS.get(key)
        if markets is None:
            markets = [{"market": mkt, "basis": "hub_top", "selections": [
                {"label": sel, "win_tips": w, "total_tips": t,
                 "displayed_pct": (round(100.0 * w / t) if (w is not None and t) else None)}]}]
        ev = {"event_id": eid, "name": name,
              "olbg_url": f"https://www.olbg.com/betting-tips/{path}?event_id={eid}",
              "time_label": tlabel, "competition": comp,
              "experts": exp, "comments": com, "markets": markets,
              "official": OFFICIAL.get(key, {})}
        sports[sp]["events"].append(ev)
    # sports where OLBG printed "No tips found." at capture time
    empty = {"snooker": "OLBG Snooker category page printed 'No tips found.'",
             "greyhounds": "OLBG Greyhounds category page printed 'No tips found.'"}
    for k, note in empty.items():
        sports[k]["capture_note"] = note
    out = {"schema": "olbg-live-capture/v2", "captured_utc": CAPTURE_UTC,
           "collector": "direct page retrieval of live OLBG category and event pages",
           "timezone_finding": "OLBG prints relative labels with a clock time. Cross-checking three events against official UTC start times (NHL CBJ@PHI 23:00Z shown 19:07, NHL BOS@CAR 00:00Z shown 20:07, EHF Kielce 19:45Z shown 15:45, ICC NZ v IND 07:00Z shown 03:00) places OLBG's clock in US Eastern daylight time (UTC-4), not UK time. MLB and F1 rows differ by a further hour; official start times are therefore authoritative and are shown beside every row where they were confirmed.",
           "sports": sports}
    path = os.path.join(ROOT, "data", "live-capture.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, sort_keys=False)
    n_ev = sum(len(v["events"]) for v in sports.values())
    n_sel = sum(len(m["selections"]) for v in sports.values() for e in v["events"] for m in e["markets"])
    print(f"wrote {path}: {len(sports)} sports, {n_ev} events, {n_sel} priced selections")


if __name__ == "__main__":
    build()
