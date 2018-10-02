from django.conf.urls import include, url

urlpatterns = [
    url(r'^GOnet/', include('gonet.urls')), 
]
