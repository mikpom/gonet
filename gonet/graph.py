import genontol
print(genontol.__file__)
import json
import networkx as nx
import numpy as np
import pandas as pd
from . import ontol
from . import cyjs
from .ontol import O, gaf, get_domain_subgraph, gene2allterms
from .geneid import _dtypes
from gonet.clry import celery_app

def add_net_data(G, gene_data, namespace, sp='human', gene2slimterms=None, enrich_res_df=None):
    if not enrich_res_df is None:
        pvals = {}
        qvals = {}
        for t in enrich_res_df.itertuples():
            pvals[t.term] = t.p
            qvals[t.term] = t.q
    else:
       pvals = None
       qvals = None
    for node in G.nodes:
        if node.startswith('GO:'): #Node is a GO term
            t = O.get_term(node)
            genes_connected = len(list(filter(lambda n: not n.startswith('GO:'),
                                              G.successors(node))))
            xgenes = []
            for gene in gene_data.index:
                if gene in set(t.node[sp]):
                    xgenes.append(gene)
            G.node[node].update({
                "data" : {
                    "id" : node,
                    "shared_name" : str(node),
                    "nodetype" : "GOterm",
                    "genes_connected" : genes_connected,
                    "xgenes" : xgenes,
                    "nodesymbol" : t.name,
                    "P" : pvals[node] if pvals else None,
                    "Padj" : qvals[node] if qvals else None,
                    "name" : str(node),
                },
                "selected" : False
            })
            
        else: #Node is a gene
            try: 
                _annots = sorted(filter(lambda t: ontol.O.get_attr(t, 'namespace')==namespace,
                                           ontol.id2go[sp][node]))
                #ontol.gene2terms[node][namespace]
            except KeyError:
                _annots = []
            allterms = [O.get_term(annot) for annot in _annots]
            slimterms = None
            # dealing with annotation task if
            # gene2slimters was provided
            if not gene2slimterms is None:
                slimterms=[]
                for term in gene2slimterms[node]:
                    slimterms.append(O.get_term(term))
            uniprot_id, ensembl_id, mgi_id, symbol, desc, identified, val = gene_data.loc[node, \
                 ['uniprot_id', 'ensembl_id', 'mgi_id', 'submit_name', 'desc', 'identified', 'val']]
            if gene_data.loc[node, 'gn_in_swp'] > 1 or gene_data.loc[node, 'syn_in_swp'] > 1:
                ambiguous = True
            else:
                ambiguous = False
            G.node[node].update({
                "data" : {
                    "id" : node,
                    "nodetype" : "gene",
                    "nodesymbol" : symbol,
                    "desc" : desc,
                    "name" : node,
                    "expr:user_supplied" : val,
                    "identified" : bool(identified),
                    "ambiguous" : ambiguous,
                    "allterms" :  [{"termid":t.id, "termname":t.name} for t in allterms ],
                    "slimterms" : [{"termid":t.id, "termname":t.name} for t in slimterms] \
                                  if slimterms else None,
                    "uniprot_id" : uniprot_id,
                    "ensembl_id" : ensembl_id,
                    "mgi_id" : mgi_id
                },
                "selected" : False
            })
    for edge in G.edges():
        if edge[0].startswith('GO:') and edge[1].startswith('GO:'):
            edgetype = 'go2go'
            target = edge[1]
            relation = O.get_relation(*edge)
        else:
            edgetype = 'go2gene'
            target = gene_data.loc[edge[1], 'submit_name']
            relation = 'annotated_with'
        G.adj[edge[0]][edge[1]].update({
                    "data" : {
                        "id" : edge[0]+'_'+edge[1],
                        "source" : G.node[edge[0]]['data']['id'],
                        "target" : G.node[edge[1]]['data']['id'],
                        "name" : edge[0]+" (interacts with) "+target,
                        "edgetype" : edgetype,
                        "relation" : relation
                    },
                    "selected" : False
                })
    if len(gene_data) < 300:
        for edge, d in filter(lambda i: i[1]['data']['edgetype']=='go2gene', G.edges.items()):
            # find those 'specific_terms' pairs (having form (gene, term))
            # satisfying gene == edge[1]
            pairs = filter(lambda p: p[0]==edge[1], O.get_attr(edge[0], 'specific_terms'))
            specific_terms = {}
            for _gene, _go_term in pairs:
                #find references; [[_go_term]] to always get Dataframe not Series
                refs = sorted(list(set(gaf[sp].loc[_gene].loc[[_go_term]]['db_reference'])))
                specific_terms[_go_term] = {'specific_term_name':O.get_attr(_go_term, 'name'),\
                                            'refs': refs }
            G.adj[edge[0]][edge[1]]['data']['specific_terms']=specific_terms
    return G



def induced_connected_subgraph(G, nodes):
    _nodes = set(nodes)
    g = nx.DiGraph()
    g.add_nodes_from(G)
    g.add_edges_from(G.edges)
    roots = list(filter(lambda n: g.in_degree(n)==0, g))
    W = set(roots)
    while len(W)>0:
        n = W.pop()
        successors = list(g.successors(n))
        if  n in _nodes:
            for successor in successors:
                W.add(successor)
        else:
            for successor in successors:
                W.add(successor)
                for predecessor in filter(lambda p: p in _nodes, g.predecessors(n)):
                    g.add_edge(predecessor, successor)
    g.remove_nodes_from(list(filter(lambda n: n not in _nodes, g)))
    g = nx.transitive_reduction(g)
    return g

@celery_app.task
def build_enrich_GOnet(enrich_res_df, qvalue, parsed_data, namespace, sp='human', jobid=None):
    df = pd.read_json(enrich_res_df)
    parsed_data = pd.read_json(parsed_data, dtype=_dtypes)
    #print('from build_enrich_GOnet', type(parsed_data.iloc['Q16873', 'mgi_id']))
    # Don't consider duplicates
    parsed_data = parsed_data[parsed_data['duplicate_of']=='']
    enrichterms = list(set(df[df['q']<qvalue]['term']))
    by_goterm = df.groupby('term')
    Gr = get_domain_subgraph(O, namespace).reverse(copy=False)
    netG = induced_connected_subgraph(Gr, enrichterms)
    for gene_id in parsed_data.index:
        netG.add_node(gene_id)
        for term in filter(lambda t: gene_id in O.get_attr(t, sp), enrichterms):
            go_successors = filter(lambda n: n.startswith('GO:') and (gene_id in O.get_attr(n, sp)),
                                   netG.successors(term))
            if (len(list(go_successors))==0):
                netG.add_edge(term, gene_id)
    G = add_net_data(netG, parsed_data, namespace, sp,
                     enrich_res_df=df)
    return json.dumps(cyjs.nx2cyjs(G))

@celery_app.task
def build_slim_GOnet(parsed_data, slim, namespace, sp='human', jobid=None):
    parsed_data = pd.read_json(parsed_data, dtype=_dtypes)
    # Don't consider duplicates
    parsed_data = parsed_data[parsed_data['duplicate_of']=='']
    if isinstance(slim, str):
        slimterms = ontol.get_slim(slim, namespace)
        Gr = get_domain_subgraph(O, namespace).reverse(copy=False)
    elif isinstance(slim, list):
        slimterms = slim
        Gr = O.G.reverse(copy=False)
    # will create new nodes
    netG = induced_connected_subgraph(Gr, slimterms)
    gene2slimterms = {}
    for gene_id in parsed_data.index:
        netG.add_node(gene_id)
        geneterms = gene2allterms[sp][gene_id].intersection(slimterms)
        gene2slimterms[gene_id] = geneterms
        for slimterm in geneterms:
            go_successors = filter(lambda n: n.startswith('GO:') and \
                                          (gene_id in O.get_attr(n, sp)),
                                     netG.successors(slimterm))
            if (len(list(go_successors))==0):
                netG.add_edge(slimterm, gene_id)
#                gene2slimterms[gene_id].add(slimterm)
    G = add_net_data(netG, parsed_data, namespace, sp, 
                     gene2slimterms=gene2slimterms)
    return json.dumps(cyjs.nx2cyjs(G))

