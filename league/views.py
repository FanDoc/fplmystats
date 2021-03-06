from django.shortcuts import redirect, render
from fplmystats.utils import league_utils
from fplmystats.forms import ContactForm
from django.urls import NoReverseMatch
from urllib.error import HTTPError
from json import JSONDecodeError

# TODO Min & Max view switch for totals in league view
# TODO Squad Statistics view for league view, every player & how many members own them
# TODO drop down menu to compare every manager for each week instead of only totals


def search(request):
    try:
        league_id = request.POST['league_id']
        return redirect('league:detail', league_id)
    except NoReverseMatch:
        return redirect('index_error', 0, 1)


def detail(request, league_id):
    try:
        contact_form = ContactForm
        name = league_utils.get_league_name(league_id)
        stats = league_utils.get_stats(league_id)

        general_number = stats.general_number_totals
        general_number_string = []
        for item in general_number:
            holder = [item[0]]
            for number in item[1:]:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            general_number_string.append(holder)

        general_points = stats.general_points_totals
        general_points_string = []
        for item in general_points:
            holder = [item[0]]
            for number in item[1:]:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            general_points_string.append(holder)

        positions = stats.positions_totals
        positions_string = []
        for item in positions:
            holder = [item[0]]
            for number in item[1:]:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            positions_string.append(holder)

        team_selection = stats.team_selection_totals
        team_selection_string = []
        for item in team_selection:
            holder = [item[0]]
            for number in item[1:]:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            team_selection_string.append(holder)

        general_number_max = stats.general_number_max
        general_number_max_string = []
        for item in general_number_max:
            holder = []
            for number in item:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            general_number_max_string.append(holder)

        general_points_max = stats.general_points_max
        general_points_max_string = []
        for item in general_points_max:
            holder = []
            for number in item:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            general_points_max_string.append(holder)

        positions_max = stats.positions_max
        positions_max_string = []
        for item in positions_max:
            holder = []
            for number in item:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            positions_max_string.append(holder)

        team_selection_max = stats.team_selection_max
        team_selection_max_string = []
        for item in team_selection_max:
            holder = []
            for number in item:
                try:
                    holder.append("{:,}".format(number))
                except ValueError:
                    holder.append(number)
            team_selection_max_string.append(holder)

        headers = stats.headers

        context = {'league_id': league_id,
                   'league_name': name,
                   'headers': headers,
                   'general_number': general_number_string,
                   'general_number_max': general_number_max_string,
                   'general_points': general_points_string,
                   'general_points_max': general_points_max_string,
                   'positions': positions_string,
                   'positions_max': positions_max_string,
                   'team_selection': team_selection_string,
                   'team_selection_max': team_selection_max_string,
                   'form': contact_form}
        return render(request, 'league/detail.html', context)
    except HTTPError:
        return redirect('index_error', 0, 1)
    except JSONDecodeError:
        return redirect('index_error', 0, 1)
