from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup
from requests import get

try:
    from lookup import lookup
    from request_utils import get_selenium_wrapper, get_wrapper
    from utils import get_player_suffix
except:
    from basketball_reference_scraper.lookup import lookup
    from basketball_reference_scraper.request_utils import (
        get_selenium_wrapper, get_wrapper)
    from basketball_reference_scraper.utils import get_player_suffix


def get_stats(
    _name, stat_type="PER_GAME", playoffs=False, career=False, ask_matches=True
):
    name = lookup(_name, ask_matches)
    suffix = get_player_suffix(name)
    if not suffix:
        return pd.DataFrame()
    stat_type = stat_type.lower()
    table = None
    if stat_type in ["per_game", "totals", "advanced"] and not playoffs:
        r = get_wrapper(f"https://www.basketball-reference.com/{suffix}")
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "html.parser")
            table = soup.find("table", {"id": stat_type})
            table = str(table)
        else:
            raise ConnectionError("Request to basketball reference failed")
    elif stat_type in ["per_minute", "per_poss"] or playoffs:
        if playoffs:
            xpath = f"//table[@id='playoffs_{stat_type}']"
        else:
            xpath = f"//table[@id='{stat_type}']"
        table = get_selenium_wrapper(
            f"https://www.basketball-reference.com/{suffix}", xpath
        )
    if table is None:
        return None
    df = pd.read_html(StringIO(table))[0]
    df.rename(
        columns={
            "Season": "SEASON",
            "Age": "AGE",
            "Tm": "TEAM",
            "Lg": "LEAGUE",
            "Pos": "POS",
            "Awards": "AWARDS",
        },
        inplace=True,
    )
    if "FG.1" in df.columns:
        df.rename(columns={"FG.1": "FG%"}, inplace=True)
    if "eFG" in df.columns:
        df.rename(columns={"eFG": "eFG%"}, inplace=True)
    if "FT.1" in df.columns:
        df.rename(columns={"FT.1": "FT%"}, inplace=True)

    career_index = df[df["SEASON"] == "Career"].index[0]
    if career:
        df = df.iloc[career_index + 2 :, :]
    else:
        df = df.iloc[:career_index, :]

    df = df.reset_index().drop("index", axis=1)
    return df


def get_game_logs(_name, year, playoffs=False, ask_matches=True):
    name = lookup(_name, ask_matches)
    suffix = get_player_suffix(name).replace(".html", "")
    if playoffs:
        selector = "pgl_basic_playoffs"
        url = f"https://www.basketball-reference.com/{suffix}/gamelog-playoffs"
    else:
        selector = "pgl_basic"
        url = f"https://www.basketball-reference.com/{suffix}/gamelog/{year}"
    r = get_wrapper(url)
    if r.status_code == 200:
        soup = BeautifulSoup(r.content, "html.parser")
        table = soup.find("table", {"id": selector})
        if table is None:
            return pd.DataFrame()
        df = pd.read_html(StringIO(str(table)))[0]
        df.rename(
            columns={
                "Date": "DATE",
                "Age": "AGE",
                "Tm": "TEAM",
                "Unnamed: 5": "HOME/AWAY",
                "Opp": "OPPONENT",
                "Unnamed: 7": "RESULT",
                "GmSc": "GAME_SCORE",
                "Series": "SERIES",
            },
            inplace=True,
        )
        df["HOME/AWAY"] = df["HOME/AWAY"].apply(
            lambda x: "AWAY" if x == "@" else "HOME"
        )
        df = df[df["Rk"] != "Rk"]
        df = df.drop(["Rk", "G"], axis=1).reset_index(drop=True)
        if not playoffs:
            df["DATE"] = pd.to_datetime(df["DATE"])
        return df
    else:
        raise ConnectionError("Request to basketball reference failed")


def get_team_and_opp_stats(team, season_end_year, data_format="TOTALS"):
    xpath = '//table[@id="team_and_opponent"]'
    table = get_selenium_wrapper(
        f"https://www.basketball-reference.com/teams/{team}/{season_end_year}.html",
        xpath,
    )
    if not table:
        raise ConnectionError("Request to basketball reference failed")

    # Read the HTML table
    df = pd.read_html(StringIO(table))[0]

    # Find where Opponent stats begin
    opp_idx = df[df["Unnamed: 0"] == "Opponent"].index[0]

    # Split into team portion and opponent portion
    df_team = df[:opp_idx]
    df_opp = df[opp_idx:]

    # Map the user's data_format to the correct row labels
    if data_format == "TOTALS":
        team_row = "Team"
        opp_row = "Opponent"
    elif data_format == "PER_GAME":
        team_row = "Team/G"
        opp_row = "Opponent/G"
    elif data_format == "RANK":
        team_row = "Lg Rank"
        opp_row = "Lg Rank"
    elif data_format == "YEAR/YEAR":
        team_row = "Year/Year"
        opp_row = "Year/Year"
    else:
        print("Invalid data format")
        return {}

    # Extract the row containing the team stats
    s_team = df_team[df_team["Unnamed: 0"] == team_row]
    s_team = s_team.drop(columns=["Unnamed: 0"]).reindex()
    s_team = pd.Series(index=s_team.columns, data=s_team.values.tolist()[0])

    # Extract the row containing the opponent stats
    s_opp = df_opp[df_opp["Unnamed: 0"] == opp_row]
    s_opp = s_opp.drop(columns=["Unnamed: 0"]).reindex()
    s_opp = pd.Series(index=s_opp.columns, data=s_opp.values.tolist()[0])

    # Rename indices to ensure uniqueness in the final Series
    s_team.index = [f"TEAM_{col}" for col in s_team.index]
    s_opp.index = [f"OPP_{col}" for col in s_opp.index]

    # Concatenate both Series into one
    combined_stats = pd.concat([s_team, s_opp])

    return combined_stats


def get_player_headshot(_name, ask_matches=True):
    name = lookup(_name, ask_matches)
    suffix = get_player_suffix(name)
    jpg = suffix.split("/")[-1].replace("html", "jpg")
    url = "https://d2cwpp38twqe55.cloudfront.net/req/202006192/images/players/" + jpg
    return url


def get_player_splits(_name, season_end_year, stat_type="PER_GAME", ask_matches=True):
    name = lookup(_name, ask_matches)
    suffix = get_player_suffix(name)[:-5]
    r = get_wrapper(
        f"https://www.basketball-reference.com/{suffix}/splits/{season_end_year}"
    )
    if r.status_code == 200:
        soup = BeautifulSoup(r.content, "html.parser")
        table = soup.find("table")
        if table:
            df = pd.read_html(StringIO(str(table)))[0]
            for i in range(1, len(df["Unnamed: 0_level_0", "Split"])):
                if isinstance(df["Unnamed: 0_level_0", "Split"][i], float):
                    df["Unnamed: 0_level_0", "Split"][i] = df[
                        "Unnamed: 0_level_0", "Split"
                    ][i - 1]
            df = df[~df["Unnamed: 1_level_0", "Value"].str.contains("Total|Value")]

            headers = df.iloc[:, :2]
            headers = headers.droplevel(0, axis=1)

            if stat_type.lower() in ["per_game", "shooting", "advanced", "totals"]:
                if stat_type.lower() == "per_game":
                    df = df["Per Game"]
                    df["Split"] = headers["Split"]
                    df["Value"] = headers["Value"]
                    cols = df.columns.tolist()
                    cols = cols[-2:] + cols[:-2]
                    df = df[cols]
                    return df
                elif stat_type.lower() == "shooting":
                    df = df["Shooting"]
                    df["Split"] = headers["Split"]
                    df["Value"] = headers["Value"]
                    cols = df.columns.tolist()
                    cols = cols[-2:] + cols[:-2]
                    df = df[cols]
                    return df

                elif stat_type.lower() == "advanced":
                    df = df["Advanced"]
                    df["Split"] = headers["Split"]
                    df["Value"] = headers["Value"]
                    cols = df.columns.tolist()
                    cols = cols[-2:] + cols[:-2]
                    df = df[cols]
                    return df
                elif stat_type.lower() == "totals":
                    df = df["Totals"]
                    df["Split"] = headers["Split"]
                    df["Value"] = headers["Value"]
                    cols = df.columns.tolist()
                    cols = cols[-2:] + cols[:-2]
                    df = df[cols]
                    return df
            else:
                raise Exception(
                    'The "stat_type" you entered does not exist. The following options are: PER_GAME, SHOOTING, ADVANCED, TOTALS'
                )
    else:
        raise ConnectionError("Request to basketball reference failed")
