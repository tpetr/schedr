from django.conf.urls.defaults import *
from django.contrib import admin

from django.views.generic.simple import direct_to_template

from schedr.base import SchedrSitemap

admin.autodiscover()

sitemaps = {
    'schools': SchedrSitemap
}

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),
# for maintenance:
    #(r'', direct_to_template, {'template': 'maintenance.html'}),

    (r'^$', 'schedr.base.views.index'),
    (r'^push_recv$', 'schedr.base.views.push_recv'),
    (r'^new$', 'schedr.base.views.index', {'template_name': 'index.dev'}),
    (r'^sitemap.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
    (r'^robots.txt$', 'schedr.base.views.robots'),
    (r'^info/press/$', direct_to_template, {'template': 'info/press.html'}),
    (r'^info/about/$', direct_to_template, {'template': 'info/about.html'}),
    (r'^info/contact/$', direct_to_template, {'template': 'info/contact.html'}),
    (r'^info/privacy/$', direct_to_template, {'template': 'info/privacy.html'}),
    (r'^help/?$', 'schedr.base.views.help'),
    (r'^account/?$', 'schedr.base.views.account'),
    (r'^account/feedback$', 'schedr.base.views.feedback'),

    (r'^home/?$', 'schedr.base.views.home'),

    # schools
    (r'^umass/', include('schedr.umass.urls')),
    (r'^northwestern/', include('schedr.northwestern.urls')),
#    (r'^amherst/', include('schedr.amherst.urls')),
    (r'^uri/', include('schedr.uri.urls')),
#    (r'^mit/', include('schedr.mit.urls')),

    # api
    (r'^api/oauth_test/$', 'api.views.oauth_test'),
    (r'^api/$', 'api.views.index'),
    (r'^api/(?P<method>.+)', 'api.views.call'),
    (r'^api-doc/$', 'api.views.list'),
    (r'^api-doc/(?P<method>.+)', 'api.views.doc'),

    (r'^oauth/', include('oauth_provider.urls')),

    # static files
    (r'^account/', include('schedr.accounts.urls')),
    (r'^break$', 'schedr.base.views.error'),
)
