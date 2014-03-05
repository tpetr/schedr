from django.contrib.syndication.feeds import Feed
from schedr.umass.models import Event, Testimonial, Term

class TermEntries(Feed):
    title = "Schedr Terms - UMass Amherst"
    link = "/terms/"
    description = "Updates on terms for UMass Amherst"
    
    def items(self):
        return Term.objects.order_by('-date')[:5]


