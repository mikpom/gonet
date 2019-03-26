'use strict';
var chai = require('chai'),
    should = chai.should(),
    assert = chai.assert,
    lytutils = require('../lyt'),
    cytoscape = require('cytoscape'),
    fs = require('fs'),
    promisetests = require('../promisetest');

describe('Read and render _COSE_ layout correctly (genelist 2)', function() {
    it('Position nodes correctly', function(done) {
        var netData = JSON.parse(fs.readFileSync('test/sampdata/genelist2_network.cyjs', 'utf8'));
        var cyInst = cytoscape({ styleEnabled: true, headless: true });
        cyInst.json(netData);
        cyInst.nodes().length.should.equal(90);
        var p = lytutils.runLyt(cyInst, "cose", true, 10);
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
            
            cyInst.destroy();
            done();
        }).catch(function(err) {
            cyInst.destroy();
            done(err);
        });
    });
});

describe('Read and render _HIERARCHICAL_ layout correctly (network1)', function() {
    
    it('Position nodes correctly with genes hidden (network1)', function(done) {
        var netData = JSON.parse(fs.readFileSync('test/sampdata/network1.cyjs', 'utf8'));
        var cyInst = cytoscape({ styleEnabled: true, headless: true });
        cyInst.json(netData);
        cyInst.nodes().length.should.equal(94);
        cyInst.nodes('[nodetype="gene"]').style({display:'none'});
        var hpad=100;
        lytutils.runLyt(cyInst, "hierarchical", true, 10, hpad).then(function (cy) {
            
            var orphans = cyInst.nodes(':visible').filter(function(n){return n.neighborhood().nodes(':visible').length==0;});
            var nonOrphans = cyInst.elements(':visible').diff(orphans).left;
            var components = nonOrphans.components().sort(function(a,b){return b.length-a.length;});
            // components should be tightly positioned with hpad of 100 as provided
            assert.equal(components[0].boundingBox().x2+hpad, components[1].boundingBox().x1);
            assert.equal(components[1].boundingBox().x2+hpad, components[2].boundingBox().x1);

            cyInst.destroy();
            done();

        }).catch(function(err) {
            console.log('Got error', err.stack);
            done(err);
        });
    });
});

describe('Read and render _HIERARCHICAL_ layout correctly', function() {
    it('Position nodes correctly (genelist2 network)', function(done) {
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
