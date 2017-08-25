from django.shortcuts import redirect, render
from fplmystats.utils import league_utils


def search(request):
    league_id = request.POST['league_id']
    return redirect('league:detail', league_id)


def detail(request, league_id):
    # TODO Error checking user input

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

    team_selection = stats.team_selection_totals

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

    headers = stats.headers

    context = {'league_id': league_id,
               'league_name': name,
               'headers': headers,
               'general_number': general_number_string,
               'general_number_max': general_number_max_string,
               'general_points': general_points_string,
               'general_points_max': general_points_max_string,
               'team_selection': team_selection}
    return render(request, 'league/detail.html', context)
