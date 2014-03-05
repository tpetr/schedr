from django.contrib.sitemaps import Sitemap
from schedr.base.models import School

class SchedrSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return School.objects.filter(visible=True)

    def lastmod(self, obj):
        return obj.last_updated
