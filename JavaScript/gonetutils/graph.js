module.exports = {transitiveReduction : transitiveReduction,
                  connectedSubgraph : connectedSubgraph,
                  hideNodes: hideNodes
                 };

function transitiveReduction(cy, subset, remove=false) {
    var tmpRemovedEdges;
        if (subset == undefined) {
        subset = cy.nodes();
    }
    else {
        tmpRemovedEdges = cy.edges().difference(subset.edgesTo(subset));
        tmpRemovedEdges.remove();
    }
        
    var edgesToRemove = cy.collection();
    subset.forEach(function(nd){
        //console.log("processing node", nd.id());
        nd.outgoers().forEach(function(outgoer) {
            //console.log("    processing outgoer", outgoer.id());
            outgoer.successors().forEach(function(sc){
                //console.log("        processing successor", sc.id());
                edgesToRemove = edgesToRemove.union(nd.edgesTo(sc));
            });
        });
    });
    if (remove==true) {
        edgesToRemove.remove();
    }

    if (tmpRemovedEdges != undefined) {
        tmpRemovedEdges.restore();
    }
    return edgesToRemove;
}
    
function connectedSubgraph(cy, subset, remove=false) {
    var roots = cy.nodes().filter(function(n){return n.indegree()==0;}).map(function(n){return n.id();});
    //console.log('roots are', roots)
    var nodes = roots;
    // console.log('roots len is ', nodes.length)
    var tmpEdgesIds = [];
    var edgeId;
    while (nodes.length > 0) {
        var curNodeId = nodes.shift();
        //console.log('processing node', curNodeId)
        var curNode = cy.getElementById(curNodeId);
        var outgoers = curNode.outgoers().nodes();
        if (subset.contains(curNode)) {
            outgoers.forEach(function(outgoerNode){nodes.push(outgoerNode.id());});
        }
        else {
            var incomers = curNode.incomers().nodes().filter(function(n){return subset.contains(n);});
            outgoers.forEach(function(outgoerNode){
                nodes.push(outgoerNode.id());
                incomers.forEach(function(incomerNode){
                    if (incomerNode.edgesTo(outgoerNode).length==0) {
                        edgeId = incomerNode.id()+'_'+outgoerNode.id();
                        cy.add({ group:"edges", data: {id: edgeId, source: incomerNode.id(),
                                                       target: outgoerNode.id()}});
                        tmpEdgesIds.push(edgeId);
                    }
                });
            });
        }
    }
    
    var nodesToRemove = cy.nodes().difference(subset);
    var tmpEdges = cy.collection(tmpEdgesIds.map(function(i){return cy.getElementById(i)}));
    var edgesToRemove = tmpEdges.intersection(nodesToRemove.connectedEdges());
    var addedEdges = tmpEdges.difference(edgesToRemove);
    if (remove==true) {
        edgesToRemove.remove();
        nodesToRemove.remove();
    }
    else {
        edgesToRemove.remove();
    }
    return addedEdges;
}


function hideNodes(cy, nodes) {
    var nodesToRetain = cy.nodes().difference(nodes);
    var addedEdges = connectedSubgraph(cy, cy.nodes().difference(nodes));
    addedEdges.remove();
    addedEdges.forEach(function(edge){
        if (edge.target().data("nodetype") == "gene") {
            edge.data("relation", "annotated_with");
        }
        else {
            var srcSelector = "#"+edge.source().id().replace(":", "\\:");
            var tgtSelector = "#"+edge.target().id().replace(":", "\\:");
            var relations = cy.elements().aStar({root:srcSelector, goal:tgtSelector, directed:true})
                .path.edges().map(function(e){return e.data("relation");});
            if (relations.includes("part_of")) {
                edge.data("relation", "part_of");
            }
            else {
                edge.data("relation", "is_a");
            }
        }
    });
    addedEdges.restore();
    nodes.style({display:'none'});
    var edgesToRemove = transitiveReduction(cy, nodesToRetain);
    edgesToRemove.remove();
    return {addedEdges:addedEdges,
            removedEdges:edgesToRemove};
    
}
