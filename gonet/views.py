import os
import uuid
import json
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
import logging
from .forms import GOnetSubmitForm
from .models import GOnetSubmission, GOnetJobStatus
from .ontol import celltype_choices
from gonet.exceptions import DataNotProvidedError, \
                                    InputValidationError
from django import urls
from django.views.decorators.csrf import csrf_exempt
import numpy as np

log = logging.getLogger(__name__)

def job_submission(request, *args, **kwargs):
    if request.method=='GET':
        return render(request, 'gonet/submit_page.html', {'form': GOnetSubmitForm()})
    elif request.method=='POST':
        form = GOnetSubmitForm(request.POST)
        if form.is_valid():
            try:
                sO = GOnetSubmission.create(form.cleaned_data, cli=request.META['REMOTE_ADDR'],
                                            genelist_file=request.FILES.get('uploaded_file', default=None),
                                            bg_file=request.FILES.get('bg_file', default=None))
                job_status = GOnetJobStatus(id=sO.id, rdy=False, err='')
                job_status.save()
                sO.run_pre_analysis()
                URL = urls.reverse('GOnet-check-analysis-progress', args=(str(sO.id), ))
                return HttpResponseRedirect(URL)
            except DataNotProvidedError as e:
                return render(request, 'gonet/err/input_errors_page.html', {'error': e.args[0]})
            except InputValidationError as e:
                return render(request, 'gonet/err/input_errors_page.html', {'error': e.args[0]})
        else:
            log.error('form is not valid with errors '+str(form.errors.as_data()),
                      extra={'jobid':'not_assigned'})
        return render(request, 'gonet/submit_page.html', {'form': form})

def check_analysis_progress(request, jobid):
    job_status = GOnetJobStatus.objects.get(pk=jobid)
    if job_status.rdy==True:
        job_err = job_status.err.split(';')
        if 'too_many_entries_for_graph' in job_err:
            return render(request, 'gonet/err/input_errors_page.html',
                          {'error': 'Lists with more than 3000 entries are '\
                           +'incompatible with output type "Graph". You may'\
                           +' use "CSV" or "TXT" instead.'})
        if 'too_many_entries' in job_err:
            return render(request, 'gonet/err/input_errors_page.html',
                          {'error': 'Maximum number of entries is 20000.'})
        sO = GOnetSubmission.objects.get(pk = jobid)
        if 'genes_not_recognized' in job_err:
            return render(request, 'gonet/err/genes_not_recognized_error_page.html',
                          {'genes': list(sO.parsed_data['submit_name'])})
        elif 'invalid_GO_terms' in job_err:
            invalid_terms = list(sO.parsed_custom_terms[sO.parsed_custom_terms['invalid']]['termid'])
            return render(request, 'gonet/err/input_errors_page.html',
                          {'error': 'Some of the custom terms provided were not found'\
                                    +' in Ontology. Check if these terms exist and'\
                                    +' and not obsolete.',
                          'invalid_entries' : invalid_terms})
        else:
            URL = urls.reverse('GOnet-run-results', args=(str(sO.id), ))
            return HttpResponseRedirect(URL)
    else:
        return render(request, 'gonet/wait_page.html', 
                     {'status_url' : urls.reverse('GOnet-job-status', args=(jobid,))})

def job_status(request, jobid):
    job_status = GOnetJobStatus.objects.get(pk=jobid)
    if job_status.rdy==True:
        resp = json.dumps({'status':'ready'})
        return HttpResponse(resp, content_type="application/json")
    else:
        resp = json.dumps({'status':'running'})
        return HttpResponse(resp, content_type="application/json")

def run_results(request, jobid):
    sO = GOnetSubmission.objects.get(pk=jobid)
    if (sO.output_type=="graph"):
        template_kwargs = {'jobid' : jobid,
                           'net_json_url' : urls.reverse('GOnet-network-json', args=(str(sO.id),)),
                           'expr_url_base': urls.reverse('GOnet-get-expression', args=(str(sO.id), '')),
                           'expr_celltypes' : celltype_choices[sO.organism].items(),
                           'analysis_type' : sO.analysis_type,
                           'organism': sO.organism,
                           'job_name':sO.job_name}
        return render(request, 'gonet/graph_result.html',
                      template_kwargs)
    elif (sO.output_type=="txt"):
        response = HttpResponse(sO.res_txt, content_type="text/plain")
        response['Content-Disposition'] = 'inline; filename= "GOnet_res.txt"'
        return response
    elif (sO.output_type=="csv"):
        response = HttpResponse(sO.res_csv, content_type="text/csv")
        response['Content-Disposition'] = 'attachement; filename= "GOnet_res.csv"'
        return response

def input_id_map(request, jobid):
    sO = GOnetSubmission.objects.get(pk=jobid)
    response = HttpResponse(sO.get_id_map(), content_type="text/csv")
    response['Content-Disposition'] = 'inline; filename= "id_map.csv"'
    return response

def bg_genename_resolve(request, jobid):
    sO = GOnetSubmission.objects.get(pk=jobid)
    df = sO.bg_genes
    resolved = df[df['nsyns']==1]['resolved_name'].to_string()
    response = HttpResponse(resolved, content_type="text/plain")
    response['Content-Disposition'] = 'inline; filename= "genes_resolved.txt"'
    return response
    
def serve_network_json(request, jobid):
    sO = GOnetSubmission.objects.get(pk = jobid)
    if 'callback' in request.GET:
        resp = request.GET['callback']+'('+sO.network+');'
        return HttpResponse(resp, content_type="application/javascript")
    else:
        return HttpResponse(sO.network, content_type="application/json")

def expr_values(request, jobid, celltype):
    if (not celltype in celltype_choices['human']) and \
       (not celltype in celltype_choices['mouse']):
        log.error(celltype + ' not supported')
    sO = GOnetSubmission.objects.get(pk = jobid)
    expr_json = sO.get_expr_json(celltype)
    if 'callback' in request.GET:
        resp = request.GET['callback']+'('+expr_json+');'
        return HttpResponse(resp, content_type="application/javascript")
    else:
        return HttpResponse(expr_json, content_type="application/json")
    
def serve_res_txt(request, jobid):
    sO = GOnetSubmission.objects.get(pk=jobid)
    if sO.res_txt=='':
        if sO.analysis_type == 'enrich':
            sO.get_enrich_res_txt()
        if sO.analysis_type == 'annot':
            sO.get_annot_res_txt()
    response = HttpResponse(sO.res_txt, content_type="text/plain")
    response['Content-Disposition'] = 'inline; filename= "GOnet_res.txt"'
    return response

def serve_res_csv(request, jobid):
    sO = GOnetSubmission.objects.get(pk=jobid)
    if sO.res_csv=='':
        if sO.analysis_type == 'enrich':
            sO.get_enrich_res_csv()
        if sO.analysis_type == 'annot':
            sO.get_annot_res_csv()
    response = HttpResponse(sO.res_csv, content_type="text/csv")
    response['Content-Disposition'] = 'attachement; filename= "GOnet_res.csv"'
    return response

def doc_part(request, doc_entry):
    if doc_entry == 'index':
        return render(request, 'gonet/docs/GOnet_docs_index.html')
    elif doc_entry == 'input':
        return render(request, 'gonet/docs/GOnet_docs_input.html')
    elif doc_entry == 'output':
        return render(request, 'gonet/docs/GOnet_docs_output.html')
    elif doc_entry == 'export':
        return render(request, 'gonet/docs/GOnet_docs_export.html')
    elif doc_entry == 'node_colors':
        return render(request, 'gonet/docs/GOnet_docs_node_colors.html')
    elif doc_entry == 'analysis_types':
        return render(request, 'gonet/docs/GOnet_docs_analysis_types.html')
    elif doc_entry == 'contact':
        return render(request, 'gonet/docs/GOnet_docs_contact.html')
    elif doc_entry == 'enrich_bg':
        return render(request, 'gonet/docs/GOnet_docs_enrich_bg.html')
    
