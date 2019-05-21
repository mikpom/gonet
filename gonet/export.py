import networkx as nx
import pandas as pd
from .clry import celery_app
from .ontol import O, get_slim


def _pprint_successors(ret, format_func, G, node, indent=1):
    for s in G.successors(node):
        ret.append(format_func(s, indent))
        _pprint_successors(ret, format_func, G, s, indent=indent+1)

@celery_app.task
def annot_txt(dfjs, slim, namespace, organism, terms=None, jobid=None):
    _df = pd.read_json(dfjs)
    df = _df[_df['duplicate_of']=='']
    if slim=='custom':
        terms = list(pd.read_json(terms)['termid'])
    else:
        terms = get_slim(slim, namespace)
    def _format_term(t, indent):
        tname = O.get_attr(t, 'name')
        termgenes = []
        for gene in df.index:
            if gene in term_subgraph.node[t][organism]:
                termgenes.append(df.loc[gene, 'submit_name'])
        return '    '*max(indent, 0)+t, tname, \
                       ', '.join(termgenes)
    term_subgraph = O.G.subgraph(terms).reverse()
    res_txt_list = []
    for component in nx.connected_components(term_subgraph.to_undirected()):
        roots = filter(lambda n: term_subgraph.in_degree(n)==0,
                       term_subgraph.subgraph(component))
        for root in roots:
            res_txt_list.append(_format_term(root, 0))
            _pprint_successors(res_txt_list, _format_term, term_subgraph, root, indent=1)
    max_first = max([len(a[0]) for a in res_txt_list])
    res_txt = ('{:<'+str(max_first+2)+'}').format('GO_term_id') \
              +'{:<80}'.format('GO_term_def') \
              +'Genes\n'
    for vals in res_txt_list:
        if len(vals[1])>80:
            term_def = vals[1][:75]+'...'
        else:
            term_def = vals[1]
        res_txt += (('{:<'+str(max_first+2)+'}').format(vals[0]) \
                    +'{:<80.80}'.format(term_def) \
                    +vals[2])
        res_txt +='\n'
    return res_txt

@celery_app.task
def enrich_txt(dfjs, enrichjs, qval, organism, jobid=None):
    _df = pd.read_json(dfjs)
    df = _df[_df['duplicate_of']=='']
    enrich_res = pd.read_json(enrichjs)
    by_term = enrich_res.groupby('term')
    def _format_term(t, indent):
        goterm = O.get_term(t)
        pval, qval = by_term.get_group(t)[['p', 'q']].values.flatten()
        term_genes = []
        for gene in _df.index:
            if gene in goterm.node[organism]:
                term_genes.append(df.loc[gene, 'submit_name'])
        return '    '*max(indent, 0)+t, goterm.name, pval, qval, ', '.join(sorted(term_genes))
    significant_terms = set(enrich_res[enrich_res['q']<qval]['term'])
    # subgraph is oriented from more general to more specific
    term_subgraph = O.G.subgraph(significant_terms).reverse()
    res_txt_list = []
    for component in nx.connected_components(term_subgraph.to_undirected()):
        roots = filter(lambda n: term_subgraph.in_degree(n)==0,
                       term_subgraph.subgraph(component))
        for root in roots:
            res_txt_list.append(_format_term(root, 0))
            _pprint_successors(res_txt_list, _format_term, term_subgraph, root, indent=1)
    if res_txt_list:
        max_first = max([len(a[0]) for a in res_txt_list])
    else:
        max_first = 20
    res_txt = ('{:<'+str(max_first+2)+'}').format('GO_term_id') \
              +'{:<80}'.format('GO_term_def') \
              +'{:<23}'.format('  P') \
              +'{:<23}'.format('  P_FDR_adjusted') \
              +'Genes\n'
    for vals in res_txt_list:
        if len(vals[1])>80:
            term_def = vals[1][:75]+'...'
        else:
            term_def = vals[1]
        res_txt += (('{:<'+str(max_first+2)+'}').format(vals[0]) \
                    +'{:<80.80}'.format(term_def) \
                    +'{:<23}'.format('  '+'{:.3E}'.format(vals[2]))
                    +'{:<23}'.format('  '+'{:.3E}'.format(vals[3])) \
                    +vals[4])
        res_txt +='\n'
    return res_txt

def get_summary_df(gene_data, terms, organism):
    """
    Collects information about terms specified in a form of a DataFrame
    """
    terms = list(terms)
    smry = pd.DataFrame(index=pd.Index(list(range(len(terms))), name='N'),
                        columns = ['GO_term_ID', 'GO_term_def', 'NofGenes', 'Genes'])
    df = gene_data[gene_data['duplicate_of']=='']
    for ind in range(len(terms)):
        termgenes = []
        term = terms[ind]
        t = O.get_term(term)
        xgenes = t.node[organism].intersection(df.index)
        termgenes = sorted(list(df.loc[xgenes, 'submit_name']))
        smry.loc[ind, ['GO_term_ID', 'GO_term_def', 'NofGenes', 'Genes']] = \
                      [term, t.name, len(termgenes), '|'.join(termgenes)]
    return smry

@celery_app.task
def enrich_csv(dfjs, enrichjs, qval, organism, jobid=None):
    df = pd.read_json(dfjs)
    enrich_df = pd.read_json(enrichjs)
    res_df = enrich_df[['term', 'p', 'q']]
    significant_terms = res_df[res_df['q']<qval]
    significant_terms = significant_terms.sort_values('p')
    smry = get_summary_df(df, significant_terms['term'], organism)
    smry['P_FDR_adj'] = significant_terms['q'].values
    smry['P'] = significant_terms['p'].values
    smry.sort_values('P', inplace=True)
    smry['asc_N'] = list(range(1, len(smry)+1))
    smry.set_index('asc_N', inplace=True)
    smry = smry[['GO_term_ID', 'GO_term_def', 'P', 'P_FDR_adj', 'NofGenes', 'Genes']]
    return smry.to_json(orient='split')

@celery_app.task
def annot_csv(dfjs, slim, namespace, organism, terms=None, jobid=None):
    df = pd.read_json(dfjs)
    if slim=='custom':
        terms = list(pd.read_json(terms)['termid'])
    else:
        terms = get_slim(slim, namespace)
    smry = get_summary_df(df, terms, organism)
    smry.sort_values('NofGenes', ascending=False, inplace=True)
    smry['asc_N'] = list(range(1, len(smry)+1))
    smry.set_index('asc_N', inplace=True)
    return smry.to_json(orient='split')

