import pandas as pd
import os
import hashlib

def generate_id(provider, raw_id):
    raw_str = f"{provider}:{raw_id}"
    return hashlib.sha1(raw_str.encode('utf-8')).hexdigest()

# 1. 创建 Minnesota Lynx 2024 核心阵容
roster_data = [
    {"Player": "Napheesa Collier", "Pos": "F", "Ht": "6-1", "Wt": "174", "Birth Date": "1996-09-23", "College": "UConn", "Exp": 5},
    {"Player": "Kayla McBride", "Pos": "G", "Ht": "5-10", "Wt": "174", "Birth Date": "1992-06-25", "College": "Notre Dame", "Exp": 10},
    {"Player": "Courtney Williams", "Pos": "G", "Ht": "5-8", "Wt": "133", "Birth Date": "1994-05-11", "College": "South Florida", "Exp": 8},
    {"Player": "Alanna Smith", "Pos": "F", "Ht": "6-4", "Wt": "180", "Birth Date": "1996-09-10", "College": "Stanford", "Exp": 5},
    {"Player": "Bridget Carleton", "Pos": "F", "Ht": "6-1", "Wt": "190", "Birth Date": "1997-05-22", "College": "Iowa State", "Exp": 5},
    {"Player": "Diamond Miller", "Pos": "G", "Ht": "6-3", "Wt": "163", "Birth Date": "2001-02-11", "College": "Maryland", "Exp": 1},
    {"Player": "Dorka Juhász", "Pos": "F", "Ht": "6-5", "Wt": "192", "Birth Date": "1999-12-18", "College": "UConn", "Exp": 1},
    {"Player": "Natisha Hiedeman", "Pos": "G", "Ht": "5-8", "Wt": "135", "Birth Date": "1997-02-10", "College": "Marquette", "Exp": 5},
    {"Player": "Cecilia Zandalasini", "Pos": "F", "Ht": "6-2", "Wt": "175", "Birth Date": "1996-03-16", "College": "", "Exp": 2}
]

df_roster = pd.DataFrame(roster_data)
df_roster['season'] = 2024
df_roster['team'] = "MIN"
df_roster['pid'] = df_roster['Player'].apply(lambda x: generate_id("wnba", x))

# 2. 创建 2024 赛季 Lynx 部分比赛数据 (Fact Games)
# 示例：前5场比赛
games_data = [
    {"date": "2024-05-14", "opponent": "SEA", "home_away": "away", "result": "W", "score_min": 83, "score_opp": 70, "top_scorer": "A. Smith (18)"},
    {"date": "2024-05-17", "opponent": "SEA", "home_away": "home", "result": "W", "score_min": 102, "score_opp": 93, "top_scorer": "N. Collier (29)"},
    {"date": "2024-05-23", "opponent": "CON", "home_away": "away", "result": "L", "score_min": 82, "score_opp": 83, "top_scorer": "N. Collier (19)"},
    {"date": "2024-05-26", "opponent": "NYL", "home_away": "home", "result": "W", "score_min": 84, "score_opp": 67, "top_scorer": "N. Collier (15)"},
    {"date": "2024-05-29", "opponent": "LVA", "home_away": "home", "result": "L", "score_min": 66, "score_opp": 80, "top_scorer": "N. Collier (18)"}
]

df_games = pd.DataFrame(games_data)
df_games['season_year'] = 2024
df_games['gid'] = df_games.apply(lambda x: generate_id("wnba", f"2024_{x['date']}_MIN"), axis=1)
df_games['team_abbr'] = 'MIN'

# 3. 保存到 Data Warehouse
os.makedirs("data_warehouse", exist_ok=True)

roster_path = "data_warehouse/minnesota_lynx_2024_roster.csv"
games_path = "data_warehouse/minnesota_lynx_2024_games.csv"

df_roster.to_csv(roster_path, index=False)
df_games.to_csv(games_path, index=False)

print(f"SUCCESS: Generated mock data for Minnesota Lynx:")
print(f" - Roster: {roster_path} ({len(df_roster)} players)")
print(f" - Games:  {games_path} ({len(df_games)} games)")
