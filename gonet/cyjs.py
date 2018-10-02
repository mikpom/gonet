import networkx as nx

def cyjs2nx(json):
    G = nx.DiGraph()
    nodeid2name = {}
    for node in json['elements']['nodes']:
        node_name = node['data']['name'] 
        G.add_node(node_name)
        G.node[node_name].update(node)
        nodeid2name[node['data']['id']] = node_name
    for edge in json['elements']['edges']:
        src, target = nodeid2name[edge['data']['source']], nodeid2name[edge['data']['target']]  
        G.add_edge(src, target)
        G.adj[src][target].update(edge)
    return G

def nx2cyjs(G):
    cyjs = {}
    cyjs['elements'] = {}
    cyjs['elements']['nodes'] = [G.node[node] for node in G.nodes()]
    cyjs['elements']['edges'] = [edge[2] for edge in G.edges(data=True)]
    return cyjs
