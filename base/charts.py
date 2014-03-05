from pygooglechart import Chart, SimpleLineChart, Axis
from datetime import date, timedelta

from base.decorators import cache_chart

from datetime import datetime

@cache_chart
def users(*args):
    days = 60
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("SELECT date_joined, COUNT(*) from auth_user where date_joined > NOW() - INTERVAL %i DAY group by DATE(date_joined) order by DATE(date_joined) desc" % days)

    data = {}
    max_y = 0;
    for dt, num in cursor.fetchall():
        if num > max_y:
            max_y = num;
        data[dt.date()] = num

    data2 = []

    dt = date.today() - timedelta(days-1)
    for i in xrange(days):
        data2.append((dt, data.get(dt, 0)))
        dt = dt + timedelta(1)

    chart = SimpleLineChart(800, 125, y_range=[0, max_y])
    chart.add_data([row[1] for row in data2])
    chart.set_colours(['0000FF'])

    ticks = (max_y % 25) + 1

    left_axis = range(0, max_y, 25)
    left_axis[0] = ''
    chart.set_axis_labels(Axis.RIGHT, left_axis)

    bottom_axis = [dt[0].strftime("%b") if dt[0].day == 1 else '' for dt in data2]
    chart.set_axis_labels(Axis.BOTTOM, bottom_axis)

    chart.set_title("Daily Registrations")

    data2.reverse() 
    return chart
