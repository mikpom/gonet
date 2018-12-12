from django.conf.urls import url
from django.contrib import admin
from . import views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^$', views.job_submission, name='GOnet-submit-form'),
    url(r'^job(?P<jobid>[^/]+)$', views.check_analysis_progress, name='GOnet-check-analysis-progress'),
    url(r'^job(?P<jobid>[^/]+)/status$', views.job_status, name='GOnet-job-status'),
    url(r'^job(?P<jobid>.+)/idmap$', views.input_id_map, name='GOnet-input-idmap'),
    url(r'^job(?P<jobid>.+)/bg_resolve$', views.bg_genename_resolve, name='GOnet-bg-resolve'),
    url(r'^job(?P<jobid>.+)/result$', views.run_results, name='GOnet-run-results'),
    url(r'^net(?P<jobid>.+)$', views.serve_network_json, name='GOnet-network-json'),
    url(r'^expr(?P<jobid>.+)/(?P<celltype>.*)$', views.expr_values, name='GOnet-get-expression'),
    url(r'^job(?P<jobid>.+)/txt_res', views.serve_res_txt, name='GOnet-txt-res'),
    url(r'^job(?P<jobid>.+)/csv_res', views.serve_res_csv, name='GOnet-csv-res'),
    url(r'^doc/(?P<doc_entry>.+)$', views.doc_part, name='doc-part'),
    url(r'^\)$', views.adhoc_job_submission, name='GOnet-adhoc-submit-form'),

]
