var cytoscape = require('cytoscape');
var dagre = require('cytoscape-dagre');
cytoscape.use( dagre );
var euler = require('cytoscape-euler');
cytoscape.use(euler);

module.exports = {runLyt : runLyt,
                  computeLytPos: computeLytPos};

var gridLyt = {
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
    sort: function(node1, node2) {
        var n1, n2;
        if (node1.data().nodetype=="gene") {n1 = 1;} else if (node1.data().nodetype=="GOterm") {n1 = 10;}
        if (node2.data().nodetype=="gene") {n2 = 1;} else if (node2.data().nodetype=="GOterm") {n2 = 10;}
        return n1 - n2;
    }, // a sorting function to order the nodes; e.g. function(a, b){ return a.data('weight') - b.data('weight') }
    animate: true, // whether to transition the node positions
    animationDuration: 300, // duration of animation in ms if enabled
    animationEasing: undefined, // easing of animation if enabled
    animateFilter: function ( node, i ){ return true; }, // a function that determines whether the node should be animated.  All nodes animated by default on animate enabled.  Non-animated nodes are positioned immediately when the layout starts
    ready: undefined, // callback on layoutready
    stop: function() {}, // callback on layoutstop
    transform: function (node, position ){ return position; }, // transform a given node position. Useful for changing flow direction in discrete layouts
    wheelSensitivity : 0.1
};    

var hierLyt = {
    name: 'dagre',
    // dagre algo options, uses default value on undefined
    nodeSep: undefined, // the separation between adjacent nodes in the same rank
    edgeSep: undefined, // the separation between adjacent edges in the same rank
    rankSep: undefined, // the separation between adjacent nodes in the same rank
    rankDir: undefined, // 'TB' for top to bottom flow, 'LR' for left to right,
    ranker: undefined, // Type of algorithm to assign a rank to each node in the input graph. Possible values: 'network-simplex', 'tight-tree' or 'longest-path'
    minLen: function( edge ){ return 1; }, // number of ranks to keep between the source and target of the edge
    edgeWeight: function( edge ){ return 1; }, // higher weight edges are generally made shorter and straighter than lower weight edges

    // general layout options
    fit: false, // whether to fit to viewport
    padding: 30, // fit padding
    spacingFactor: undefined, // Applies a multiplicative factor (>0) to expand or compress the overall area that the nodes take up
    nodeDimensionsIncludeLabels: undefined, // whether labels should be included in determining the space used by a node (default true)
    animate: false, // whether to transition the node positions
    animateFilter: function( node, i ){ return true; }, // whether to animate specific nodes when animation is on; non-animated nodes immediately go to their final positions
    animationDuration: 200, // duration of animation in ms if enabled
    animationEasing: undefined, // easing of animation if enabled
    boundingBox: undefined, // constrain layout bounds; { x1, y1, x2, y2 } or { x1, y1, w, h }
    transform: function( node, pos ){ return pos; }, // a function that applies a transform to the final node position
    ready: function(){}, // on layoutready
    stop: function(){} // on layoutstop
};

var coseLyt = {
  name: 'cose',
  ready: function(){}, // Called on `layoutready`
  stop: function(){}, // Called on `layoutstop`
  // Whether to animate while running the layout
  // true : Animate continuously as the layout is running
  // false : Just show the end result
  // 'end' : Animate with the end result, from the initial positions to the end positions
  animate: false, // or 'end'
  animationEasing: undefined, // Easing of the animation for animate:'end'
  animationDuration: 0, // The duration of the animation for animate:'end'
  animateFilter: function ( node, i ){ return true; }, // A function that determines whether the node should be animated
  animationThreshold: 10000, // The layout animates only after this many milliseconds for animate:true (prevents flashing on fast runs)
  // Number of iterations between consecutive screen positions update
  // (0 -> only updated on the end)
  refresh: 1000,
  fit: false, // Whether to fit the network view after when done
  padding: 30, // Padding on fit
  boundingBox: undefined, // Constrain layout bounds; { x1, y1, x2, y2 } or { x1, y1, w, h }
  nodeDimensionsIncludeLabels: false, // Excludes the label when calculating node bounding boxes for the layout algorithm
  randomize: false, // Randomize the initial positions of the nodes (true) or use existing positions (false)
  componentSpacing: 100, // Extra spacing between components in non-compound graphs
  // Node repulsion (non overlapping) multiplier
  nodeRepulsion: function( node ){
      var repulsion = 6*2048;
      if (node.data().nodetype=="gene") {
            if (node.degree()==0) {
                repulsion = 0.1 * repulsion;}
            else {
                repulsion = repulsion;}
        }
        else if (node.data().nodetype=="GOterm") {
            repulsion=repulsion*1000;};
        return repulsion;
    },
  nodeOverlap: 8, // Node repulsion (overlapping) multiplier
  idealEdgeLength: function( edge ){ return 32; }, // Ideal edge (non nested) length
  edgeElasticity: function( edge ){ return 32; }, // Divisor to compute edge forces
  nestingFactor: 1.2, // Nesting factor (multiplier) to compute ideal edge length for nested edges
  gravity: 1, // Gravity force (constant)
  numIter: 1000, // Maximum number of iterations to perform
  initialTemp: 1000, // Initial temperature (maximum node displacement)
  coolingFactor: 0.99, // Cooling factor (how the temperature is reduced between consecutive iterations
  minTemp: 1.0, // Lower temperature threshold (below this point the layout will end)
  weaver: false // Pass a reference to weaver to use threads for calculations
};


var eulerLyt = {
    name: 'euler',

    // The ideal length of a spring
    // - This acts as a hint for the edge length
    // - The edge length can be longer or shorter if the forces are set to extreme values
    springLength: edge => 200,

    // Hooke's law coefficient
    // - The value ranges on [0, 1]
    // - Lower values give looser springs
    // - Higher values give tighter springs
    springCoeff: edge => 0.0008,

    // The mass of the node in the physics simulation
    // - The mass affects the gravity node repulsion/attraction
    mass: function(node) {
        if (node.data().nodetype=="gene") {
            return 4;
        }
        else if (node.data().nodetype=="GOterm") {
            return 10;
        }
    },

    // Coulomb's law coefficient
    // - Makes the nodes repel each other for negative values
    // - Makes the nodes attract each other for positive values
    gravity: -1.2,

    // A force that pulls nodes towards the origin (0, 0)
    // Higher values keep the components less spread out
    pull: 0.001,

    // Theta coefficient from Barnes-Hut simulation
    // - Value ranges on [0, 1]
    // - Performance is better with smaller values
    // - Very small values may not create enough force to give a good result
    theta: 0.666,

    // Friction / drag coefficient to make the system stabilise over time
    dragCoeff: 0.02,

    // When the total of the squared position deltas is less than this value, the simulation ends
    movementThreshold: 1,

    // The amount of time passed per tick
    // - Larger values result in faster runtimes but might spread things out too far
    // - Smaller values produce more accurate results
    timeStep: 20,

    // The number of ticks per frame for animate:true
    // - A larger value reduces rendering cost but can be jerky
    // - A smaller value increases rendering cost but is smoother
    refresh: 10,

    // Whether to animate the layout
    // - true : Animate while the layout is running
    // - false : Just show the end result
    // - 'end' : Animate directly to the end result
    animate: false,

    // Animation duration used for animate:'end'
    animationDuration: undefined,

    // Easing for animate:'end'
    animationEasing: undefined,

    // Maximum iterations and time (in ms) before the layout will bail out
    // - A large value may allow for a better result
    // - A small value may make the layout end prematurely
    // - The layout may stop before this if it has settled
    maxIterations: 1000,
    maxSimulationTime: 4000,

    // Prevent the user grabbing nodes during the layout (usually with animate:true)
    ungrabifyWhileSimulating: false,

    // Whether to fit the viewport to the repositioned graph
    // true : Fits at end of layout for animate:false or animate:'end'; fits on each frame for animate:true
    fit: false,

    // Padding in rendered co-ordinates around the layout
    padding: 30,

    // Constrain layout bounds with one of
    // - { x1, y1, x2, y2 }
    // - { x1, y1, w, h }
    // - undefined / null : Unconstrained
    boundingBox: undefined,

    // Layout event callbacks; equivalent to `layout.one('layoutready', callback)` for example
    ready: function(){}, // on layoutready
    stop: function(){}, // on layoutstop

    // Whether to randomize the initial positions of the nodes
    // true : Use random positions within the bounding box
    // false : Use the current node positions as the initial positions
    randomize: false
};

// define layouts dictionary
var layoutOpts = {"cose":coseLyt, "euler":eulerLyt, "hierarchical":hierLyt, "grid":gridLyt};

function runLyt(cy, lytName, animate=true, animationDuration=500, hpad=200) {
    var orphans = cy.nodes(':visible').filter(function(n){return n.neighborhood().nodes(':visible').length==0;});
    var nonOrphans = cy.elements(':visible').diff(orphans).left;
    // components are sorted  < large network, ..., small network >
    if (animate==true) {
        return runLytAnimated(cy=cy, orphans=orphans, nonOrphans=nonOrphans,
                              lytName=lytName, animationDuration=animationDuration,
                              hpad=hpad);
    }
}

function runLytAnimated(cy, orphans, nonOrphans, lytName, animationDuration, hpad) {
    var lytOpts = layoutOpts[lytName];
    var components = nonOrphans.components().sort(function(a,b){return b.length-a.length;});
    var animPromises = [];

    // This computes the layouts and puts the nodes back
    var computePosPromises = components.map(function(comp) {
        return computeLytPos(cy, comp, lytName);
    });
    var nonOrphanPromise = components.reduce(function(curPromise, comp, compIndex) {
        var _p = Promise.all([computePosPromises[compIndex], curPromise]).then(function(values) {
            var computedPos = values[0];
            var anchorBbox = values[1];
            
            var shift = {x : anchorBbox.xmax - computedPos.xmin + hpad,
                         y : anchorBbox.ymin - computedPos.ymin};
            comp.forEach(function(ele) {
                var anim = ele.animation({position : {x:computedPos.x[ele.id()]+shift.x,
                                                      y:computedPos.y[ele.id()]+shift.y},
                                          duration:animationDuration});
                animPromises.push(anim.promise());
                anim.play();
            });
            return {xmin: anchorBbox.xmin,
                    xmax: anchorBbox.xmax+computedPos.w+hpad,
                    ymin: anchorBbox.ymin,
                    ymax: Math.max(anchorBbox.ymax, computedPos.h)};
        }).catch(function(err){
            throw err;
        });
        return _p;
    }, new Promise(function(resolve) {resolve({xmin :0, xmax:0, ymin:0, ymax:0});}));
    
    var globalLytPromise = nonOrphanPromise.then(function(bbox) {
        return positionOrphans(cy, orphans, {x:bbox.xmin, y:bbox.ymax+200}, animationDuration);
    }).catch(function(err){
            throw err;
    }).then(function(val) {
        return Promise.all(animPromises);
    });
    return globalLytPromise;
}

function computeLytPos(cy, eles, lytname) {
    var computedPos = {x : Object(), y : Object(),
                       xmin : undefined, ymin : undefined,
                       xmax : undefined, ymax : undefined};
    cy.startBatch();
    var initPositions = eles.map(function(ele) {
        return Object.assign({}, ele.position()); // Trick to create a copy
    });
    var lyt = eles.layout(layoutOpts[lytname]);
    var promise = lyt.promiseOn("layoutstop").then(function() {
        eles.forEach(function(ele) {
            computedPos.x[ele.id()] = ele.position().x;
            computedPos.y[ele.id()] = ele.position().y;
        });
        var bbox = eles.boundingBox();
        computedPos.xmin = bbox.x1;
        computedPos.xmax = bbox.x2;
        computedPos.ymin = bbox.y1;
        computedPos.ymax = bbox.y2; 
        computedPos.w = bbox.w;
        computedPos.h = bbox.h;
        eles.forEach(function(ele, eleIndex) {
            ele.position(initPositions[eleIndex]);
        });
        return computedPos;
    }).catch(function(err){
        throw err;
    });
    lyt.run();
    cy.endBatch();
    return promise;
}

function positionOrphans(cy, orphans, pos, animationDuration) {
    var orphanBbox = {
        x1 : pos.x,
        y1 : pos.y,
        w  : 10000.0,
        h  : 10000.0
    };
    
    var lytOpts = layoutOpts['grid'];
    lytOpts.animationDuration = animationDuration;
    lytOpts.boundingBox = orphanBbox;
    var lyt = orphans.layout(lytOpts);
    var _p = lyt.promiseOn("layoutstop");
    lyt.run();
    return _p;
}
