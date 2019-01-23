'use strict';
var chai = require('chai'),
    should = chai.should(),
    assert = chai.assert,
    lytutils = require('../lyt'),
    cytoscape = require('cytoscape'),
    fs = require('fs'),
    promisetests = require('../promisetest');

// describe('Read and render layout correctly (genelist 3)', function() {
//     it('should return correct number of nodes', function() {
//         var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist3_network.cyjs', 'utf8'));
//         var cy = cytoscape()
//         cy.json(netData)
//         cy.nodes().length.should.equal(321);
//     });
//     it('Position nodes correctly', function() {
//         var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist3_network.cyjs', 'utf8'));
//         var cy = cytoscape();
//         cy.json(netData);
//         cy.nodes('[nodetype="gene"]').style({display:'none'});
//         lytutils.runLyt(cy, "hierarchical", 0, function () {
//             assert.deepEqual(cy.getElementById("GO:0002682").position(), { x: 345.25, y: 127.5 });
//             assert.deepEqual(cy.getElementById("GO:0008283").position(), { x: 155.5, y: 1090.5 });
//         });
//     });
// });

describe('Read and render _COSE_ layout correctly (genelist 2)', function() {
    it('Position nodes correctly', function(done) {
        console.log(">>>beginning of IT");
        var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist2_network.cyjs', 'utf8'));
        var cyInst = cytoscape({ styleEnabled: true, headless: true });
        cyInst.json(netData);
        cyInst.nodes().length.should.equal(90);
        var p = lytutils.runLyt(cyInst, "cose", true, 10);
        console.log('>>>runLyt promise', p);
        p.then(function () {
            var orphans = cyInst.nodes(':visible').filter(function(n){return n.neighborhood().nodes(':visible').length==0;});
            var nonOrphans = cyInst.elements(':visible').diff(orphans).left;
            // components are sorted  < large network, ..., small network >
            var components = nonOrphans.components().sort(function(a,b){return b.length-a.length;});
            assert.equal(components[0].boundingBox().y1, components[1].boundingBox().y1);

            var termBbox = cyInst.nodes('[nodetype="GOterm"]').boundingBox();
            // MMP25 (Q9NPA2) is orpan node so should be below all enriched terms
            assert.isAbove(cyInst.getElementById("Q9NPA2").position().y, termBbox.y2);
            assert.isAbove(termBbox.h, 5);
            
            cyInst.destroy();
            done();
        }).catch(function(err) {
            console.log('>>>Got error', err.stack);
            cyInst.destroy();
            done(err);
        });
    });
});

describe("Test computeLytPos function", function() {
    it("Should return correct elements positions", function(done) {
        var netData = JSON.parse(fs.readFileSync("test/sampdata/genelist2_network.cyjs", "utf8"));
        var cyInst = cytoscape({ styleEnabled: true, headless: true });
        cyInst.json(netData);
        
        lytutils.computeLytPos(cyInst, cyInst.nodes(), "grid").then(function(pos) {
            var xPos = cyInst.nodes().map(function(ele) {return pos.x[ele.id()];});
            var xPosSet = new Set(xPos);
            assert.equal(xPosSet.size, 10);

            var xPosMin = xPos.reduce(function(a, b) {return Math.min(a, b);});
            assert.equal(xPosMin, pos.xmin);
            
            cyInst.destroy();
            done();
        }).catch(function(err) {
            cyInst.destroy();
            done(err);
        });
    });
});

describe('Read and render _HIERARCHICAL_ layout correctly (genelist 2)', function() {
    it('Position nodes correctly', function(done) {
        var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist2_network.cyjs', 'utf8'));
        var cyInst = cytoscape({ styleEnabled: true, headless: true });
        cyInst.json(netData);
        cyInst.nodes().length.should.equal(90);
        lytutils.runLyt(cyInst, "hierarchical", true, 10).then(function (cy) {
            var MMP25Position = cyInst.getElementById("Q9NPA2").position();
            var termBbox = cyInst.nodes('[nodetype="GOterm"]').boundingBox();
            // MMP25 is orpan node so should be below all enriched terms
            assert.isAbove(MMP25Position.y, termBbox.y2);
            assert.isAbove(termBbox.h, 100);
            // GO:2000520 belong to the smallest component so should be
            // rightmost
            assert.isAbove(cyInst.getElementById("GO:2000520").position().x,
                           cyInst.nodes('[nodetype="GOterm"]').
                           difference(cyInst.getElementById("GO:2000520"))
                           .max(function(e){return e.position().y;}).value);
            // GO:0006323 should be higher than all of its successors
            var dnaPackagingPos = cyInst.getElementById("GO:0006323").position();
            var successorsBbox = cyInst.getElementById("GO:0006323").successors().nodes().boundingBox();
            console.log("dnaPackagingPos", dnaPackagingPos);
            console.log("successorsBbox", successorsBbox);
            assert.isBelow(dnaPackagingPos.y, successorsBbox.y1);
            cyInst.destroy();
            done();
            // assert.isBelow(.y,
            //                cy.getElementById("GO:0006323").successors()
            //                .nodes().min(function(e){
            //                    return e.position().y;
            //                }).value);
        }).catch(function(err) {
            console.log('Got error', err.stack);
            done(err);
        });
    });
});


// describe('testing promise objects', function() {
//     it('resolve simple promise', function(done) {
//         var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist2_network.cyjs', 'utf8'));
//         var cy = cytoscape();
//         cy.json(netData);
//         promisetests.testpromise(cy).then(function(val){
//             assert.deepEqual(val, 90);
//             done();
//         }).catch(function(err) {
//             done(err);
//         });
//     });
//     it('resolve promise with grid layout', function(done) {
//         var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist2_network.cyjs', 'utf8'));
//         var cy = cytoscape({ styleEnabled: true, headless: true});
//         cy.json(netData);
//         promisetests.runlayout(cy).then(function(cy){
//             //cy.nodes().forEach(function(n){console.log(n.position());});
//             assert.deepEqual(cy.nodes().length, 90);
//             cy.destroy();
//             done();
//         }).catch(function(err) {
//             done(err);
//         });
//     });
//     it('move one node to (100, 100) with positionNode func', function(done) {
//         var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist2_network.cyjs', 'utf8'));
//         var cy = cytoscape({ styleEnabled: true, headless: true});
//         cy.json(netData);
//         promisetests.positionNode(cy, "GO:2000520").then(function(cy) {
//             assert.deepEqual(cy.getElementById("GO:2000520").position(), {x:100, y:100});
//             cy.destroy();
//             done();
//         }).catch(function(err) {
//             done(err);
//         });
//     });
    
//     it('move one node to (100, 100) with animation func', function(done) {
//         var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist2_network.cyjs', 'utf8'));
//         //var cy = cytoscape({ styleEnabled: true, headless: true });
//         var cy = cytoscape({ styleEnabled: true});
//         cy.json(netData);
//         promisetests.animateNode(cy, "GO:2000520").then(function(){
//             assert.deepEqual(cy.getElementById("GO:2000520").position(), {x:100, y:100});
//             cy.destroy();
//         }).then(function() {
//             done();
//         }).catch(function(err) {
//             done(err);
//         });
//     });
// });
