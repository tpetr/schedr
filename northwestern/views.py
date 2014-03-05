from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext

from schedr.northwestern.forms import CAESARLoginForm

def nu_location(request, location_name, Location, school, room=''):
    try:
        loc = Location.objects.get(name=location_name)
        if loc.school_id is None:
            raise Exception()
    except:
        return render_to_response('school/northwestern/location_wrong.html')

    if loc.name == 'TECH':
        return HttpResponseRedirect('http://www.tech.northwestern.edu/maps/roomfinder.php?room=%s' % room)
  
    return HttpResponseRedirect("http://aquavite.northwestern.edu/maps/buildinglookup.cgi?lookupid=%s" % loc.school_id)

def register_login(request):
#    if request.method == 'POST':
#        form = CAESARLoginForm(data=request.POST)
#        if form.is_valid():
#            return HttpResponseRedirect('https://ses.ent.northwestern.edu/psc/caesar/EMPLOYEE/HRMS/c/SA_LEARNER_SERVICES.SSR_SSENRL_CART.GBL?pslnkid=NW_SS_SA_ENRLMNT')
#    else:
#        form = CAESARLoginForm()
#
#    context = RequestContext(request)
#
    return render_to_response('school/northwestern/register_login.html')#, {'form': form}, context_instance=context)
