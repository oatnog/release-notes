from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^relnotes/', include('relnotes.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/(.*)', admin.site.root),
	# changes app
	#(r'^changes/$', 'relnotes.changesgrabber.views.changes'),
	(r'^static_files/(?P<path>.*)$', 'django.views.static.serve',
		{'document_root': settings.STATIC_DOC_ROOT}),
	(r'^', 'relnotes.changesgrabber.views.changes'),

)
