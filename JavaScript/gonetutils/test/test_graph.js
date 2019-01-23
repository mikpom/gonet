var chai = require('chai'),
    should = chai.should(),
    assert = chai.assert,
    graphutils = require('../graph'),
    cytoscape = require('cytoscape'),
    fs = require('fs');

//         One of the components in graph graph.mycyjs
//                  GO:0010556 ------>      GO:2000113
//                 /    |     \                 /
//                /     |      \               /
// GO:0051253    /      |       \             /
//     \        /       |        \           /
//      \      /        |         \         /
//      *GO:1902679 <- GO:2001141  \       /
//        \             |           ------/--------
//         \            |                /         \
//          \        GO:1903506 ---------------> GO:0006355
//           \        /                 /          |
//         *GO:1903507                 /           |
//                   \                /            |
//                    ------> GO:0045892  <---------

describe('Return correct number of nodes and edges', function(){
    var netData = JSON.parse(fs.readFileSync('test/sampdata/graph.mycyjs', 'utf8'));
    var cy = cytoscape();
    cy.json(netData);
    it('correct nodes', function() {
        cy.nodes().length.should.equal(21);
    });
    it('correct edges', function() {
        cy.edges().length.should.equal(21);
    });
});

describe('Test transitive reduction', function(){
    var netData = JSON.parse(fs.readFileSync('test/sampdata/graph.mycyjs', 'utf8'));
    var cy = cytoscape();
    it('should return correct number of outgoers', function() {
        cy.json(netData);
        cy.nodes().length.should.equal(21);
        cy.add({ group:"edges", data: {id: 'redundant_edge_1',
                                       source: 'GO:0010556', target: 'GO:1903506'}});
        cy.add({ group:"edges", data: {id: 'redundant_edge_2',
                                       source: 'GO:0010556', target: 'GO:0045892'}});
        var actualOutgoers = cy.getElementById('GO:0010556').outgoers().nodes();
        assert.equal(6, actualOutgoers.length);
        graphutils.transitiveReduction(cy, undefined, true);
        actualOutgoers = cy.getElementById('GO:0010556').outgoers().nodes();
        assert.equal(2, actualOutgoers.length);
        var expectedOutgoersIDs = ['GO:2001141', 'GO:2000113'];
        var expectedOutgoers = cy.filter(function(e){return expectedOutgoersIDs.includes(e.id());});
        var actualOutgoers = cy.getElementById('GO:0010556').outgoers().nodes();
        assert.isTrue(expectedOutgoers.same(actualOutgoers));
    });
    it('should return correct number of outgoers (no removal)', function() {
        cy.json(netData);
        var edgesToRemove = graphutils.transitiveReduction(cy);
        var actualOutgoers = cy.getElementById('GO:0010556').outgoers().nodes();
        assert.equal(actualOutgoers.length, 4);
        var e = cy.getElementById('GO:0010556').edgesTo(cy.getElementById('GO:0006355'));
        assert.isTrue(edgesToRemove.contains(e));
        var e2 = cy.getElementById('GO:0010556').edgesTo(cy.getElementById('GO:1902679'));
        assert.isTrue(edgesToRemove.contains(e2));
    });
});

describe('Test transitive reduction with subset', function() {
    var netData = JSON.parse(fs.readFileSync('test/sampdata/graph.mycyjs', 'utf8'));
    var cy = cytoscape();
    it('should return correct number of outgoers', function() {
        cy.json(netData);
        cy.nodes().length.should.equal(21);

        var subsetNodeIds = ["GO:0010556", "GO:2001141", "GO:1902679", "GO:0006355"];
        var subsetCol = cy.nodes().filter(function(n){return subsetNodeIds.includes(n.id());});
        var expectedToRetain = cy.getElementById("GO:0010556").edgesTo(cy.getElementById("GO:0006355"));
        var expectedToRemove = cy.getElementById("GO:0010556").edgesTo(cy.getElementById("GO:1902679"));
        assert.equal(expectedToRetain.length, 1);
        assert.equal(expectedToRemove.length, 1);

        var edgesToRemove = graphutils.transitiveReduction(cy, subsetCol);

        assert.isTrue(edgesToRemove.contains(expectedToRemove));
        assert.isFalse(edgesToRemove.contains(expectedToRetain));
    });
});


describe('Test connected subgraph on small subnetwork', function() {
    var netData = JSON.parse(fs.readFileSync('test/sampdata/graph.mycyjs', 'utf8'));
    var cy = cytoscape()

    it('return correct number of nodes;', function() {
        cy.json(netData)
        cy.nodes().length.should.equal(21);
    });

    it('return correct subgraph #1', function(){
        // GO:0051253 -> GO:0045892
        cy.json(netData)
        // take all the component above except GO:1903507 and GO:1902679
        var subset = ['GO:1903506', 'GO:0045892', 'GO:0051253', 'GO:0010556',
                      'GO:2000113', 'GO:0006355', 'GO:2001141']
        var edgesAdded = graphutils.connectedSubgraph(cy, cy.filter(function(e){return subset.includes(e.id())}), true)
        //check added edges
        var e = cy.getElementById('GO:0010556').edgesTo(cy.getElementById('GO:0045892'))
        assert.isTrue(edgesAdded.contains(e))

        var actualOutgoersIDs = cy.getElementById('GO:0051253').outgoers().nodes().map(function(n){return n.id()})
        assert.sameMembers(['GO:0045892'], actualOutgoersIDs)

        var actualOutgoersIDs = cy.getElementById('GO:0010556').outgoers().nodes().map(function(n){return n.id()})
        assert.sameMembers(actualOutgoersIDs, ['GO:2001141', 'GO:2000113', 'GO:0045892', 'GO:0006355'])
    })
    it('return correct subgraph #1 (without removal)', function(){
        // GO:0051253 -> GO:0045892
        cy.json(netData);
        // take all the component above except GO:1903507 and GO:1902679
        var subset = ['GO:1903506', 'GO:0045892', 'GO:0051253', 'GO:0010556',
                      'GO:2000113', 'GO:0006355', 'GO:2001141'];
        //console.log('incomers of GO:1902679', cy.getElementById('GO:1902679').incomers())
        var edgesAdded = graphutils.connectedSubgraph(cy, cy.filter(function(e){return subset.includes(e.id());}));
//        console.log('incomers of GO:1902679', cy.getElementById('GO:1902679').incomers())
        //check added edges
        var e = cy.getElementById('GO:0010556').edgesTo(cy.getElementById('GO:0045892'));
        assert.isTrue(edgesAdded.contains(e));

        var actualOutgoersIDs = cy.getElementById('GO:0051253').outgoers().nodes().map(function(n){return n.id()});
        assert.sameMembers(actualOutgoersIDs, ['GO:0045892', 'GO:1902679']);

        actualOutgoersIDs = cy.getElementById('GO:0010556').outgoers().nodes().map(function(n){return n.id()});
        assert.sameMembers(actualOutgoersIDs, ['GO:2001141', 'GO:2000113', 'GO:0045892', 'GO:0006355', 'GO:1902679']);
    });

});

describe("Test connected subgraph (genelist 3 example)", function() {
    it("Add necessary edges", function() {
        var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist3_network_V02.cyjs', 'utf8'));
        var cy = cytoscape({ styleEnabled: true, headless: true });
        cy.json(netData);
        cy.nodes().length.should.equal(321);
        var edge = cy.getElementById("GO:0040011").edgesTo(cy.getElementById("GO:0016477"));
        assert.equal(edge.length, 0);

        var nodesToRetain = cy.nodes('[nodetype="GOterm"]').filter(function(n) {return n.data('P')<=3.28e-7;});
        assert.equal(nodesToRetain.length, 78);
        var addedEdges = graphutils.connectedSubgraph(cy, nodesToRetain);

        edge = cy.getElementById("GO:0040011").edgesTo(cy.getElementById("GO:0016477"));
        assert.isTrue(addedEdges.contains(edge));
        assert.equal(edge.length, 1);
        assert.isTrue(edge.visible());

        cy.destroy();
    });
});

describe("Test _hide_ by Pvalue (genelist 3 example)", function() {
    it("reconstruct correct subgraph", function(done) {
        
        //        Small chunk from genelist3_network
        //        Marked with asterisk have P value > 3.28e-7
        //
        //                  GO:0040011                        
        //                 /          \                  
        //                /            \                
        //               /              \              
        //              /                \            
        //             /                  \          
        //      *GO:0048870             *GO:0042330           
        //          \                       |               
        //           \                      |                
        //            \                     V                       
        //             \                    |                
        //          GO:0016477              |                
        //                   \              |                
        //                    ------> GO:0060326            
        
        var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist3_network_V03.cyjs', 'utf8'));
        var cy = cytoscape({ styleEnabled: true, headless: true });
        cy.json(netData);
        cy.nodes('[nodetype="GOterm"]').length.should.equal(97);
        var nodesToHide = cy.nodes('[nodetype="GOterm"]').filter(function(n) {return n.data('P')>3.28e-7;});
        //nodesToHide.style({display:'none'});
        console.log('Number of nodes to hide', nodesToHide.length);
        var ee = graphutils.hideNodes(cy, nodesToHide);
        assert.equal(cy.nodes('[nodetype="GOterm"]:visible').length, 78);
        assert.equal(ee.addedEdges.length, 192);

        var e1 = cy.getElementById("GO:0040011").edgesTo(cy.getElementById("GO:0016477"));
        assert.equal(e1.length, 1);
        assert.isTrue(e1.visible());

        cy.destroy();
        done();
    });
    
    it("reconstruct correct subgraph #2", function(done) {

        //         One of the components in graph graph.mycyjs
        //         Marked with * have P value > 2.0e-10  == is_a, -- part_of
        //
        //        *GO:0023052            GO:0007154
        //              \                  /
        //               \                /
        //                \              /
        //                 \            /
        //                  \          /
        //                  *GO:0007165     
        //                       ||    
        //                       ||   
        //                       VV                        
        //                   GO:0007166     
        
        var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist3_network_V03.cyjs', 'utf8'));
        var cy = cytoscape({ styleEnabled: true, headless: true });
        cy.json(netData);
        cy.nodes('[nodetype="GOterm"]').length.should.equal(97);
        var nodesToHide = cy.nodes('[nodetype="GOterm"]').filter(function(n) {return n.data('P')>2e-10;});
        var ee = graphutils.hideNodes(cy, nodesToHide);
        assert.equal(cy.nodes('[nodetype="GOterm"]:visible').length, 41);

        var e1 = cy.getElementById("GO:0007154").edgesTo(cy.getElementById("GO:0007166"));
        assert.equal(e1.length, 1);
        assert.equal(e1.data('relation'), 'part_of');

        cy.destroy();
        done();
    });

    it("reconstruct correct subgraph #2", function(done) {

        //         One of the components in graph graph.mycyjs
        //         Marked with * have P 
        //
        //       GO:0050896   ... ->
        //           |
        //           | is_a
        //           |
        //       GO:0009605
        //           |          
        //           | is_a;part_of      
        //           |      
        //       GO:0002237   <-- ...
        //       
        //       
        //       
        
        var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist3_network_V03.cyjs', 'utf8'));
        var cy = cytoscape({ styleEnabled: true, headless: true });
        cy.json(netData);
        cy.nodes('[nodetype="GOterm"]').length.should.equal(97);
        var _ids = ["GO:0050896", "GO:0002237"];
        var nodesToRetain = cy.nodes().filter(function(n){return _ids.includes(n.id());});
        var nodesToHide = cy.nodes().difference(nodesToRetain);

        assert.equal(nodesToRetain.length, 2);
        assert.equal(nodesToHide.length, 319);
        
        var ee = graphutils.hideNodes(cy, nodesToHide);
        assert.equal(cy.nodes('[nodetype="GOterm"]:visible').length, 2);

        var e1 = cy.getElementById("GO:0050896").edgesTo(cy.getElementById("GO:0002237"));
        assert.equal(e1.length, 1);
        assert.equal(e1.data('relation'), 'is_a');

        cy.destroy();
        done();
    });
});
