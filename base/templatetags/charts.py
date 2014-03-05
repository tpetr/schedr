from django import template
from pygooglechart import Chart

register = template.Library()

class GoogleChartNode(template.Node):
    def __init__(self, chart):
        # make sure we're not doing something stupid...
        if not isinstance(chart, Chart):
            raise template.TemplateSyntaxError, "Graph method does not return instance of pygooglechart.Chart!"
        self.chart = chart

    def render(self, context):
        return '<img src="%s" width="%s" height="%s">' % (self.chart.get_url(), self.chart.width, self.chart.height)

@register.tag
def chart(parser, token):
    try:
        data = token.split_contents()
        app_name, chart_name, args = data[1], data[2], data[3:]

        charts = __import__('schedr.%s' % app_name, globals(), locals(), ['charts']).charts

        chart_func = getattr(charts, chart_name)
    except Exception, e:
        raise template.TemplateSyntaxError, "Error: %s" % e

    return GoogleChartNode(chart_func(*args))
    
