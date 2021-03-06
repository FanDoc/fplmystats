from collections import namedtuple
from fplmystats.utils import utils
from urllib.error import HTTPError
import urllib.request
import sqlite3
import json
import math

static_url = 'https://fantasy.premierleague.com/drf/bootstrap-static'
manager_info_url = 'https://fantasy.premierleague.com/drf/entry/'

with open('/home/admin/fplmystats/fplmystats/utils/current_season.txt') as file:
# with open('C:\\Users\\seanh\\PycharmProjects\\fplmystats\\fplmystats\\utils\\current_season.txt') as file:
    for x in file:
        current_season = x

data_file = '/home/admin/fplmystats/FPLdb.sqlite'
# data_file = 'FPLdb.sqlite'

MINUTES_LESS_THAN_SIXTY_VALUE = 1
MINUTES_SIXTY_PLUS_VALUE = 2
GOAL_GK_DEF_VALUE = 6
GOAL_MID_VALUE = 5
GOAL_FWD_VALUE = 4
ASSIST_VALUE = 3
CLEAN_SHEET_GK_DEF_VALUE = 4
CLEAN_SHEET_MID_VALUE = 1
SAVES_DIVIDER = 3
GOALS_CONCEDED_DIVIDER = -2
PENALTIES_SAVED_VALUE = 5
YELLOW_CARDS_VALUE = -1
RED_CARDS_VALUE = -3
PENALTIES_MISSED_VALUE = -2
OWN_GOALS_VALUE = -2


def get_name_and_team(manager_id):
    """
    Return the name and team name of the manager
    """
    names = namedtuple('names', ('manager_name', 'team_name'))
    data_url = manager_info_url + str(manager_id)
    with urllib.request.urlopen('{}'.format(data_url)) as url:
        data = json.loads(url.read().decode())

    names.manager_name = data['entry']['player_first_name'] + ' ' + data['entry']['player_last_name']
    names.team_name = data['entry']['name']
    return names


def get_stats(manager_id):
    """
    Return the data for every table in the manager view
    """
    table_data = namedtuple('table_data', ('headers', 'general_number', 'general_number_totals', 'general_points',
                                           'general_points_totals', 'positions', 'positions_totals', 'team_selection',
                                           'team_selection_totals', 'max_teams', 'squad_stats_players',
                                           'squad_stats_teams'))

    with urllib.request.urlopen('{}'.format(static_url)) as static_json:
        static_data = json.loads(static_json.read().decode())
    current_week = 0
    for event in static_data['events']:
        if event['is_current']:
            current_week = event['id']

    conn = sqlite3.connect(data_file)
    c = conn.cursor()
    player_table = '{}playerIDs'.format(str(current_season))
    week = 1    # always starts at 1

    table_data.general_number = []     # contains the number of goals, assists etc. for each week
    table_data.general_points = []     # contains the number of points obtained via goals, assists etc. for each week
    table_data.positions = []          # contains the number of points obtained via DEFs, MIDs etc. for each week
    table_data.team_selection = []     # contains the captain, MVP, bench information etc.
    table_data.max_teams = []          # contains the best team lineup for each week

    formation_dict = {'5-4-1': 0,      # used for counting occurrences of each formation
                      '5-3-2': 0,
                      '5-2-3': 0,
                      '4-5-1': 0,
                      '4-4-2': 0,
                      '4-3-3': 0,
                      '3-5-2': 0,
                      '3-4-3': 0}

    player_apps_xi_dict = {}           # records the number of times a player has appeared in the starting XI
    player_apps_xv_dict = {}           # records the number of times a player has appeared in the squad
    player_captain_dict = {}           # records the number of times a player has been captained
    player_points_dict = {}            # records the number of points obtained via each player
    teams_dict = {}                    # records the number of times a player from each team has appeared in the XI
    price_dict = {}                    # holds prices of each player

    # populate teams dictionary with all 20 teams
    c.execute('SELECT name from "{}teamIDs"'.format(str(current_season)))
    teams = c.fetchall()
    for team in teams:
        teams_dict[team[0]] = 0

    active_weeks = 0
    total_points = 0
    highest_points = 0
    highest_rank = 0

    while week <= current_week:
        week_string = str(week)
        weekly_table = '{}week{}'.format(current_season, week_string)
        picks_url = 'https://fantasy.premierleague.com/drf/entry/{}/event/{}/picks'.format(manager_id, week_string)

        pitch_ids = []             # holds ids of players who are on pitch
        bench_ids = []             # holds ids of players who are on bench
        points_list = []           # holds a list of each players points and position
        second_points_list = []    # holds players who didn't play
        points_on_pitch = 0
        bench_points = 0
        captain_id = 0
        captain_name = ''
        captain_points = 0
        captain_played = False
        vice_captain_id = 0
        vice_captain_name = ''
        vice_captain_points = 0
        vice_captain_played = False
        mvp_name = 0
        mvp_points = 0

        # add empty lists to each section to be filled with the week's data
        table_data.general_number.append([0] * 15)
        table_data.general_points.append([0] * 15)
        table_data.positions.append([0] * 13)
        table_data.team_selection.append([0] * 14)
        formation = [0, 0, 0]

        # add links for each week
        link_address = 'https://fantasy.premierleague.com/a/team/{}/event/{}'.format(manager_id, week)
        table_data.general_number[week - 1][0] = link_address
        table_data.general_points[week - 1][0] = link_address
        table_data.positions[week - 1][0] = link_address
        table_data.team_selection[week - 1][0] = link_address

        # set first element of each section to the current working week
        table_data.general_number[week - 1][1] = week
        table_data.general_points[week - 1][1] = week
        table_data.positions[week - 1][1] = week
        table_data.team_selection[week - 1][1] = week

        try:
            with urllib.request.urlopen('{}'.format(picks_url)) as url:
                data = json.loads(url.read().decode())

            active_weeks += 1
            captain_multiplier = 2
            bench_boost = False
            chip = data['active_chip']
            if chip == '3xc':
                table_data.team_selection[week - 1][2] = 'Triple Captain'
                captain_multiplier = 3
            elif chip == 'bboost':
                table_data.team_selection[week - 1][2] = 'Bench Boost'
                bench_boost = True
            elif chip == 'freehit':
                table_data.team_selection[week - 1][2] = 'Free Hit'
            elif chip == 'wildcard':
                table_data.team_selection[week - 1][2] = 'Wildcard'
            else:
                table_data.team_selection[week - 1][2] = '-'
            table_data.team_selection[week - 1][3] = data['entry_history']['event_transfers_cost']

            week_points = data['entry_history']['points']
            if week_points > highest_points:
                highest_points = week_points
            week_rank = data['entry_history']['rank']
            if week_rank is not None:
                if active_weeks == 1:
                    highest_rank = week_rank
                else:
                    if week_rank < highest_rank:
                        highest_rank = week_rank
            total_points += week_points

            total_value = data['entry_history']['value'] / 10.0

            for pick in data['picks']:
                if bench_boost:
                    pitch_ids.append([pick['element'], pick['multiplier']])
                    if pick['is_captain']:
                        captain_id = pick['element']
                    if pick['is_vice_captain']:
                        vice_captain_id = pick['element']
                else:
                    if pick['position'] <= 11:
                        pitch_ids.append([pick['element'], pick['multiplier']])
                    else:
                        bench_ids.append(pick['element'])
                    if pick['is_captain']:
                        captain_id = pick['element']
                    if pick['is_vice_captain']:
                        vice_captain_id = pick['element']

            for player_id in pitch_ids:
                player_id_string = str(player_id[0])

                c.execute('SELECT webname, firstname, secondname, position, teamID FROM "{}" WHERE id = {}'
                          .format(player_table, player_id_string))
                result = c.fetchone()

                # set name equal to first name + second name or webname if webname different to second name
                if result[0] == result[2]:
                    player_name = result[1] + ' ' + result[2]
                else:
                    player_name = result[0]
                position = result[3]
                team_id = result[4]

                if player_name not in player_points_dict:
                    player_points_dict[player_name] = 0
                    player_apps_xv_dict[player_name] = 0
                if player_name not in player_apps_xi_dict:
                    player_apps_xi_dict[player_name] = 0

                player_apps_xi_dict[player_name] += 1
                player_apps_xv_dict[player_name] += 1

                c.execute('SELECT name from "{}teamIDs" WHERE id = {}'.format(current_season, team_id))
                team_name = c.fetchone()[0]
                teams_dict[team_name] += 1

                c.execute('SELECT * FROM "{}" WHERE id = {}'.format(weekly_table, player_id_string))
                player_datum = c.fetchone()
                if player_datum is not None:
                    price = player_datum[14] / 1.0
                    if player_name not in price_dict:
                        price_dict[player_name] = [price, 1]
                    else:
                        price_dict[player_name][0] += price
                        price_dict[player_name][1] += 1

                    if player_datum[2] > 0:  # if minutes > 0
                        points_list.append([player_datum[1], position, player_name])  # points, position, player_name
                    else:
                        second_points_list.append([player_datum[1], position, player_name])
                    points_on_pitch += player_datum[1]

                    if player_datum[0] == captain_id:
                        captain_name = player_name
                        captain_points = player_datum[1]
                        if player_datum[2] > 0:
                            captain_played = True
                    elif player_datum[0] == vice_captain_id:
                        vice_captain_name = player_name
                        vice_captain_points = player_datum[1]
                        if player_datum[2] > 0:
                            vice_captain_played = True

                    # subtract clean sheets from MID's and FWD's for general_number and ignore goals conceded
                    if position == 3 or position == 4:
                        table_data.general_number[week - 1][6] -= player_datum[5]
                        table_data.general_number[week - 1][8] -= player_datum[7]

                    # Populate general number table
                    table_data.general_number[week - 1][2:15] = [sum(n) for n in zip(
                        table_data.general_number[week - 1][2:15], player_datum[1:14])]

                    # Populate general points table
                    table_data.general_points[week - 1][2] += player_datum[1]                               # points
                    if player_datum[2] == 0:                                                                # minutes
                        table_data.general_points[week - 1][3] += 0
                    elif player_datum[2] < 60:
                        table_data.general_points[week - 1][3] += MINUTES_LESS_THAN_SIXTY_VALUE
                    else:
                        table_data.general_points[week - 1][3] += MINUTES_SIXTY_PLUS_VALUE

                    if position == 1 or position == 2:                                                    # goals
                        table_data.general_points[week - 1][4] += player_datum[3] * GOAL_GK_DEF_VALUE
                    elif position == 3:
                        table_data.general_points[week - 1][4] += player_datum[3] * GOAL_MID_VALUE
                    else:
                        table_data.general_points[week - 1][4] += player_datum[3] * GOAL_FWD_VALUE

                    table_data.general_points[week - 1][5] += player_datum[4] * ASSIST_VALUE              # assists

                    if position == 1 or position == 2:                                                    # clean sheets
                        table_data.general_points[week - 1][6] += player_datum[5] * CLEAN_SHEET_GK_DEF_VALUE
                    elif position == 3:
                        table_data.general_points[week - 1][6] += player_datum[5] * CLEAN_SHEET_MID_VALUE

                    table_data.general_points[week - 1][7] += math.floor(player_datum[6] / SAVES_DIVIDER)  # saves

                    if position == 1 or position == 2:                                                    # goals conc
                        table_data.general_points[week - 1][8] += math.ceil(player_datum[7] / GOALS_CONCEDED_DIVIDER)

                    table_data.general_points[week - 1][9] += player_datum[8] * PENALTIES_SAVED_VALUE     # penes saved
                    table_data.general_points[week - 1][10] += player_datum[9] * YELLOW_CARDS_VALUE       # yellows
                    table_data.general_points[week - 1][11] += player_datum[10] * RED_CARDS_VALUE         # reds
                    table_data.general_points[week - 1][12] += player_datum[11] * PENALTIES_MISSED_VALUE  # pens missed
                    table_data.general_points[week - 1][13] += player_datum[12] * OWN_GOALS_VALUE         # own goals
                    table_data.general_points[week - 1][14] += player_datum[13]                           # bonus points

                    player_points_dict[player_name] += player_datum[1] * player_id[1]

                    if player_datum[1] > mvp_points:
                        mvp_points = player_datum[1]
                        mvp_name = player_name

                    if position == 1:
                        table_data.positions[week - 1][4] += price
                        table_data.positions[week - 1][5] += player_datum[1]
                    elif position == 2:
                        table_data.positions[week - 1][6] += price
                        table_data.positions[week - 1][7] += player_datum[1]
                        formation[0] += 1
                    elif position == 3:
                        table_data.positions[week - 1][8] += price
                        table_data.positions[week - 1][9] += player_datum[1]
                        formation[1] += 1
                    elif position == 4:
                        table_data.positions[week - 1][10] += price
                        table_data.positions[week - 1][11] += player_datum[1]
                        formation[2] += 1
                else:
                    utils.update_weekly_table()
                    get_stats(manager_id)

            table_data.positions[week - 1][4] = round(table_data.positions[week - 1][4], 1)
            table_data.positions[week - 1][6] = round(table_data.positions[week - 1][6], 1)
            table_data.positions[week - 1][8] = round(table_data.positions[week - 1][8], 1)
            table_data.positions[week - 1][10] = round(table_data.positions[week - 1][10], 1)

            for player_id in bench_ids:
                player_id_string = str(player_id)

                c.execute('SELECT webname, firstname, secondname, position FROM "{}" WHERE id = {}'
                          .format(player_table, player_id_string))
                result = c.fetchone()

                # set name equal to first second + second name or webname if webname different to second name
                if result[0] == result[2]:
                    player_name = result[1] + ' ' + result[2]
                else:
                    player_name = result[0]
                position = result[3]

                if player_name not in player_points_dict:
                    player_points_dict[player_name] = 0
                    player_apps_xv_dict[player_name] = 0

                player_apps_xv_dict[player_name] += 1

                c.execute('SELECT * FROM "{}" WHERE id = {}'.format(weekly_table, player_id_string))
                player_datum = c.fetchone()

                if player_datum is not None:
                    price = player_datum[14] / 1.0
                    if player_name not in price_dict:
                        price_dict[player_name] = [price, 1]
                    else:
                        price_dict[player_name][0] += price
                        price_dict[player_name][1] += 1
                    table_data.positions[week - 1][12] += price

                    if player_datum[0] == captain_id:
                        captain_name = player_name
                        captain_points = player_datum[1]
                        if player_datum[2] > 0:
                            captain_played = True
                    elif player_datum[0] == vice_captain_id:
                        vice_captain_name = player_name
                        vice_captain_points = player_datum[1]
                        if player_datum[2] > 0:
                            vice_captain_played = True

                    if player_datum[1] > mvp_points:
                        mvp_points = player_datum[1]
                        mvp_name = player_name

                    if player_datum[2] > 0:
                        points_list.append([player_datum[1], position, player_name])  # points, position, player_name
                    bench_points += player_datum[1]

            table_data.positions[week - 1][12] = round(table_data.positions[week - 1][12], 1)

            string_formation = '4-4-2'  # default formation if db not updated
            if formation == [5, 4, 1]:
                string_formation = '5-4-1'
            elif formation == [5, 3, 2]:
                string_formation = '5-3-2'
            elif formation == [5, 2, 3]:
                string_formation = '5-2-3'
            elif formation == [4, 5, 1]:
                string_formation = '4-5-1'
            elif formation == [4, 4, 2]:
                string_formation = '4-4-2'
            elif formation == [4, 3, 3]:
                string_formation = '4-3-3'
            elif formation == [3, 5, 2]:
                string_formation = '3-5-2'
            elif formation == [3, 4, 3]:
                string_formation = '3-4-3'

            formation_dict[string_formation] += 1
            table_data.positions[week - 1][2] = string_formation

            team_value = round(total_value, 1)
            table_data.positions[week - 1][3] = team_value

            max_points_on_pitch = 0
            points_list.sort()
            points_list = points_list[::-1]
            max_points_team = []

            if not bench_boost:
                try:
                    max_points_on_pitch += next(item[0] for item in points_list if item[1] == 1)  # 1 goalkeeper
                    max_points_team.append(next(item for item in points_list if item[1] == 1))
                    points_list.remove(next(item for item in points_list if item[1] == 1))
                    points_list.remove(next(item for item in points_list if item[1] == 1))
                except StopIteration:
                    ''
                if len(max_points_team) < 1:
                    try:
                        max_points_team.append(next(item for item in second_points_list if item[1] == 1))
                        second_points_list.remove(next(item for item in second_points_list if item[1] == 1))
                    except StopIteration:
                        ''

                for i in range(3):                                                                # 3 defenders
                    try:
                        max_points_on_pitch += next(item[0] for item in points_list if item[1] == 2)
                        max_points_team.append(next(item for item in points_list if item[1] == 2))
                        points_list.remove(next(item for item in points_list if item[1] == 2))
                    except StopIteration:
                        ''
                while len(max_points_team) < 4:
                    try:
                        max_points_team.append(next(item for item in second_points_list if item[1] == 2))
                        second_points_list.remove(next(item for item in second_points_list if item[1] == 2))
                    except StopIteration:
                        ''

                for i in range(2):                                                                # 2 midfielders
                    try:
                        max_points_on_pitch += next(item[0] for item in points_list if item[1] == 3)
                        max_points_team.append(next(item for item in points_list if item[1] == 3))
                        points_list.remove(next(item for item in points_list if item[1] == 3))
                    except StopIteration:
                        ''
                while len(max_points_team) < 6:
                    try:
                        max_points_team.append(next(item for item in second_points_list if item[1] == 3))
                        second_points_list.remove(next(item for item in second_points_list if item[1] == 3))
                    except StopIteration:
                        ''

                try:
                    max_points_on_pitch += next(item[0] for item in points_list if item[1] == 4)  # 1 forward
                    max_points_team.append(next(item for item in points_list if item[1] == 4))
                    points_list.remove(next(item for item in points_list if item[1] == 4))
                except StopIteration:
                    ''
                while len(max_points_team) < 7:
                    try:
                        max_points_team.append(next(item for item in second_points_list if item[1] == 4))
                        second_points_list.remove(next(item for item in second_points_list if item[1] == 4))
                    except StopIteration:
                        ''

                for i in range(4):                                                                # 4 remaining players
                    try:
                        max_points_on_pitch += next(item[0] for item in points_list)
                        max_points_team.append(next(item for item in points_list))
                        points_list.remove(next(item for item in points_list))
                    except StopIteration:
                        ''
                while len(max_points_team) < 11:
                    try:
                        max_points_team.append(next(item for item in second_points_list))
                        second_points_list.remove(next(item for item in second_points_list))
                    except StopIteration:
                        ''

                bench_potential_lost = max_points_on_pitch - points_on_pitch
            else:
                while len(points_list) > 0:
                    try:
                        max_points_team.append(next(item for item in points_list))
                        points_list.remove(next(item for item in points_list))
                    except StopIteration:
                        ''
                while len(second_points_list) > 0:
                    try:
                        max_points_team.append(next(item for item in second_points_list))
                        second_points_list.remove(next(item for item in second_points_list))
                    except StopIteration:
                        ''
                bench_potential_lost = 0

            if bench_potential_lost < 0:
                bench_potential_lost = 0

            # assign the captain in max team and then sort by position
            if max_points_team:
                max_points_team.sort()
                max_points_team[-1][2] = max_points_team[-1][2] + ' (C)'
                max_points_team[-1][0] = max_points_team[-1][0] * captain_multiplier
                max_points_team = sorted(max_points_team, key=lambda l: l[1])
                for player in max_points_team:
                    if player[1] == 1:
                        player[1] = 'GK'
                    elif player[1] == 2:
                        player[1] = 'DEF'
                    elif player[1] == 3:
                        player[1] = 'MID'
                    else:
                        player[1] = 'FWD'

            if captain_played or not vice_captain_played:
                table_data.team_selection[week - 1][4] = captain_name
                table_data.team_selection[week - 1][5] = captain_points * captain_multiplier
                if captain_name not in player_captain_dict:
                    player_captain_dict[captain_name] = 0
                player_captain_dict[captain_name] += 1
            else:
                table_data.team_selection[week - 1][4] = vice_captain_name
                table_data.team_selection[week - 1][5] = vice_captain_points * captain_multiplier
                captain_points = vice_captain_points
                if vice_captain_name not in player_captain_dict:
                    player_captain_dict[vice_captain_name] = 0
                player_captain_dict[vice_captain_name] += 1

            table_data.team_selection[week - 1][6] = mvp_name
            table_data.team_selection[week - 1][7] = mvp_points
            table_data.team_selection[week - 1][8] = (mvp_points - captain_points) * (captain_multiplier - 1)
            table_data.team_selection[week - 1][9] = bench_points
            table_data.team_selection[week - 1][10] = bench_potential_lost
            table_data.team_selection[week - 1][11] = int(table_data.general_points[week - 1][2] +
                                                          ((captain_points * captain_multiplier) - captain_points)
                                                          - table_data.team_selection[week - 1][3])
            table_data.team_selection[week - 1][13] = table_data.team_selection[week - 1][8] +\
                table_data.team_selection[week - 1][10]
            table_data.team_selection[week - 1][12] = table_data.team_selection[week - 1][11] +\
                table_data.team_selection[week - 1][13]

            max_points_team = [table_data.team_selection[week - 1][12]] + max_points_team      # total points
            max_points_team = [table_data.team_selection[week - 1][3] * -1] + max_points_team  # transfer cost
            max_points_team = [table_data.team_selection[week - 1][12]                         # total points - tc
                               + table_data.team_selection[week - 1][3]] + max_points_team
            max_points_team = [week] + max_points_team

            table_data.max_teams.append(max_points_team)

            week += 1
        except HTTPError:
            week += 1

    table_data.general_number_totals = [n for n in zip(*table_data.general_number)][2:16]
    table_data.general_number_totals = [sum(n) for n in table_data.general_number_totals]
    table_data.general_points_totals = [n for n in zip(*table_data.general_points)][2:16]
    table_data.general_points_totals = [sum(n) for n in table_data.general_points_totals]

    table_data.positions_totals = [0] * 10
    table_data.positions_totals[0] = round(sum(entry[3] for entry in table_data.positions) / active_weeks, 1)
    table_data.positions_totals[1] = round(sum(entry[4] for entry in table_data.positions) / active_weeks, 1)
    table_data.positions_totals[2] = sum(entry[5] for entry in table_data.positions)
    table_data.positions_totals[3] = round(sum(entry[6] for entry in table_data.positions) / active_weeks, 1)
    table_data.positions_totals[4] = sum(entry[7] for entry in table_data.positions)
    table_data.positions_totals[5] = round(sum(entry[12] for entry in table_data.positions) / active_weeks, 1)
    table_data.positions_totals[6] = round(sum(entry[8] for entry in table_data.positions) / active_weeks, 1)
    table_data.positions_totals[7] = sum(entry[9] for entry in table_data.positions)
    table_data.positions_totals[8] = round(sum(entry[10] for entry in table_data.positions) / active_weeks, 1)
    table_data.positions_totals[9] = sum(entry[11] for entry in table_data.positions)

    table_data.team_selection_totals = [0]*8
    table_data.team_selection_totals[0] = sum(entry[3] for entry in table_data.team_selection)    # transfer cost
    table_data.team_selection_totals[1] = sum(entry[5] for entry in table_data.team_selection)    # captain points
    table_data.team_selection_totals[2] = sum(entry[7] for entry in table_data.team_selection)    # mvp total
    table_data.team_selection_totals[3] = sum(entry[8] for entry in table_data.team_selection)    # captain lost
    table_data.team_selection_totals[4] = sum(entry[9] for entry in table_data.team_selection)   # bench points
    table_data.team_selection_totals[5] = sum(entry[10] for entry in table_data.team_selection)    # bench lost
    table_data.team_selection_totals[6] = sum(entry[12] for entry in table_data.team_selection)   # max possible
    table_data.team_selection_totals[7] = sum(entry[13] for entry in table_data.team_selection)   # all lost

    table_data.squad_stats_players = []
    for player in player_apps_xv_dict:
        name = player
        weeks_in_xi = 0
        weeks_in_xv = player_apps_xv_dict[player]
        weeks_captain = 0
        points = 0
        player_value = round(price_dict[player][0] / price_dict[player][1], 1)

        if player in player_apps_xi_dict:
            weeks_in_xi = player_apps_xi_dict[player]
        if player in player_captain_dict:
            weeks_captain = player_captain_dict[player]
        if player in player_points_dict:
            points = player_points_dict[player]

        # TODO fix negative points ppg & vapm
        points_per_game = 0.0
        if weeks_in_xi != 0:
            points_per_game = round(points / weeks_in_xi, 1)

        value_added_per_million = 0.0
        if weeks_in_xi != 0:
            value_added_per_million = round((points_per_game - 2) / player_value, 2)

        table_data.squad_stats_players.append([name, weeks_in_xi, weeks_in_xv, weeks_captain, points,
                                              points_per_game, value_added_per_million])

    table_data.squad_stats_teams = []
    for team in teams_dict:
        table_data.squad_stats_teams.append([team, teams_dict[team]])

    table_data.headers = [0] * 7
    table_data.headers[0] = sum(entry[11] for entry in table_data.team_selection)
    table_data.headers[1] = highest_points
    table_data.headers[2] = highest_rank
    table_data.headers[3] = max(player_captain_dict, key=player_captain_dict.get)
    table_data.headers[4] = max(player_points_dict, key=player_points_dict.get)
    table_data.headers[5] = player_points_dict[table_data.headers[4]]
    table_data.headers[6] = max(formation_dict, key=formation_dict.get)

    return table_data
