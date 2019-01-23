'use strict';
module.exports = {testpromise:testpromise,
                  runlayout:runlayout,
                  animateNode:animateNode,
                  positionNode:positionNode};

var gridLyt;

function testpromise(cy) {
    var nofnodes;
    return new Promise(function(resolve, reject){
        nofnodes = cy.nodes().length;
        resolve(nofnodes);
    });
    // promise.then(function(cy) {
    //     nofnodes = cy.nodes().length;
    //     console.log('inside then', cy.nodes().length);
    // });
    // console.log('inside testpromise', nofnodes);
    // return nofnodes;
    // return promise;
}

function runlayout(cy) {
    var promise = new Promise(function(resolve, reject){
        resolve(cy);
    });
    promise.then(function(cy) {
        var lyt = cy.nodes().layout(gridLyt);
        lyt.run();
    }, function(err){
        console.log(err.stack);
        throw err;
    });
    return promise;
}

function positionNode(cy, nodeId) {
    var ele = cy.getElementById(nodeId);
    var promise = new Promise(function(resolve, reject){
        resolve(cy);
    });
    var _p = promise.then(function(){
        ele.position({x:100, y:100});
        return cy;
    });
    return _p;
}

function animateNode(cy, nodeId) {
    var ele = cy.getElementById(nodeId);
    var anim = ele.animation({position:{x:100, y:100}, duration:0});
    var promise = new Promise(function(resolve, reject){
        resolve(cy);
    });
    var _p = promise.then(function(){
        anim.play();
        return anim.promise();
    });
    return _p;
}

gridLyt = {
    name: 'grid',
    fit: false, // whether to fit the viewport to the graph
    padding: 30, // padding used on fit
    boundingBox: undefined, // constrain layout bounds; { x1, y1, x2, y2 } or { x1, y1, w, h }
    avoidOverlap: true, // prevents node overlap, may overflow boundingBox if not enough space
    avoidOverlapPadding: 10, // extra spacing around nodes when avoidOverlap: true
    nodeDimensionsIncludeLabels: false, // Excludes the label when calculating node bounding boxes for the layout algorithm
    spacingFactor: undefined, // Applies a multiplicative factor (>0) to expand or compress the overall area that the nodes take up
    condense: true, // uses all available space on false, uses minimal space on true
    rows: undefined, // force num of rows in the grid
    cols: 10, // force num of columns in the grid
    position: function( node ){}, // returns { row, col } for element
    sort: function(node1, node2){
        var n1, n2
        if (node1.data().nodetype=="gene") {n1 = 1} else if (node1.data().nodetype=="GOterm") {n1 = 10}
        if (node2.data().nodetype=="gene") {n2 = 1} else if (node2.data().nodetype=="GOterm") {n2 = 10}
        return n1 - n2
    }, // a sorting function to order the nodes; e.g. function(a, b){ return a.data('weight') - b.data('weight') }
    animate: false, // whether to transition the node positions
    animationDuration: 300, // duration of animation in ms if enabled
    animationEasing: undefined, // easing of animation if enabled
    animateFilter: function ( node, i ){ return true; }, // a function that determines whether the node should be animated.  All nodes animated by default on animate enabled.  Non-animated nodes are positioned immediately when the layout starts
    ready: undefined, // callback on layoutready
    stop: undefined, // callback on layoutstop
    transform: function (node, position ){ return position; }, // transform a given node position. Useful for changing flow direction in discrete layouts
    wheelSensitivity : 0.1
};    
