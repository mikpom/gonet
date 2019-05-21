var $ =  require("jquery");
require("expose-loader?$!jquery");
require("expose-loader?jQuery!jquery");
import 'bootstrap';
var cytoscape = require('cytoscape');
require("expose-loader?cytoscape!cytoscape");
import {select as d3select, selectAll as d3selectAll} from "d3-selection";
import {scaleSequential, scaleLog} from "d3-scale";
import {interpolateBuGn, interpolateRdYlBu} from "d3-scale-chromatic";
var b64toBlob = require('b64-to-blob');
var FileSaver = require('file-saver');
var contextMenus = require('cytoscape-context-menus');
var graphutils = require('gonetutils/graph');
var createBinThresholds = require('gonetutils/numeric').createBinThresholds;
var runLyt = require('gonetutils/lyt').runLyt;
var mgiIcon = require("../static/figs/mgi_favicon.png");
var uniprotIcon = require("../static/figs/uniprot_favicon.png");
var ensemblIcon = require("../static/figs/ensembl_favicon.png");
var diceIcon = require("../static/figs/dice_favicon.png");
var genecardsIcon = require("../static/figs/genecards_favicon.png");
var spinnerIcon = require("../static/figs/spinner.gif");

var cy;
var currentGeneColorScale;
var currentSelectedGene;
var parentsRemoved = false;
var parentNodes;
var geneNodesRemoved=false;
var geneNodes;
var termNodes;
var tapEvent;
var imgContent;
var defaultEdges;

var aspects = {biological_process:'P',
               molecular_function:'F',
               cellular_component:'C'};

var aspectPriority = {biological_process:0,
                      molecular_function:1,
                      cellular_component:2};

var cytoscapeStyle = [ {
    "selector" : "node",
    "css" : {
        "border-width" : 1.0,
        "width" : 75.0,
        "shape" : "ellipse",
        "font-size" : 12,
        "color" : "rgb(0,0,0)",
        "font-weight" : "normal",
        "background-opacity" : 1.0,
        "text-valign" : "center",
        "text-halign" : "center",
        "border-color" : "rgb(204,204,204)",
        "text-opacity" : 1.0,
        "height" : 35.0,
        "background-color" : "rgb(137,208,245)",
        "border-opacity" : 1.0,
        "label" : "data(nodesymbol)",
        "text-wrap" : "wrap",
        "text-max-width" : "100px"
    }
}, {
    "selector" : "node[nodetype = 'GOterm']",
    "css" : {
        "shape" : "roundrectangle",
        "background-color" : "rgb(0,204,204)",
        "height" : 50.0,
        "width" : 100.0
    }
},{
    "selector" : "node.noColorData[nodetype='gene']",
    "css" : {
        "background-color":"rgb(255, 255, 255)"
    }
},{
    "selector" : "node.noColorData[nodetype='GOterm']",
    "css" : {
        "background-color":interpolateBuGn(0.3)
    }
},{
        "selector" : "node:selected",
        "css" : {
            "background-color" : "rgb(255,255,0)"
        }
    }, {
        "selector" : "edge",
        "css" : {
            "opacity" : 1.0,
            "source-arrow-shape" : "none",
            "line-color" : "rgb(132,132,132)",
            "font-weight" : "normal",
            "target-arrow-shape" : "triangle",
            "target-arrow-color" : "rgb(0,0,0)",
            "source-arrow-color" : "rgb(0,0,0)",
            "text-opacity" : 1.0,
            "color" : "rgb(0,0,0)",
            "font-size" : 10,
            "line-style" : "solid",
            "content" : "",
            "mid-target-arrow-shape" : "triangle",
            "width" : 2.0
        }
    }, {
        "selector" : "edge:selected",
        "css" : {
            "line-color" : "rgb(255,0,0)"
        }
    }, {
        "selector" : "edge[edgetype = 'go2gene']",
        "css" : {
            "mid-target-arrow-color":"rgb(132,132,132)",
            "arrow-scale" : "0.65",
            "width" : 1.5
        }
    }, {
        "selector" : "edge[edgetype = 'go2go']",
        "css" : {
            "mid-target-arrow-color":"rgb(132,132,132)",
            "arrow-scale" : "0.9",
            "width" : 2.0
        }
    }, {
        "selector" : "edge[relation = 'is_a']",
        "css" : {
            "line-style":"solid"
        }
    },{
        "selector" : "edge[relation = 'is_a;part_of']",
        "css" : {
            "line-style":"solid"
        }
    },{
        "selector" : "edge[relation = 'part_of']",
        "css" : {
            "line-style":"dashed"
        }
    },{
        "selector" : "edge[relation = 'part_of some']",
        "css" : {
            "line-style":"dashed"
        }
    }];

var contextMenuOptions = {
    // List of initial menu items
    menuItems: [
        // {
        //     id: 'remove', // ID of menu item
        //     content: 'remove', // Display content of menu item
        //     tooltipText: 'remove', // Tooltip text for menu item
        //     image: {src : "remove.svg", width : 12, height : 12, x : 6, y : 4}, // menu icon
        //     // Filters the elements to have this menu item on cxttap
        //     // If the selector is not truthy no elements will have this menu item on cxttap
        //     selector: 'node, edge', 
        //     onClickFunction: function () { // The function to be executed on click
        //         console.log('remove element');
        //     },
        //     disabled: false, // Whether the item will be created as disabled
        //     show: false, // Whether the item will be shown or not
        //     hasTrailingDivider: true, // Whether the item will have a trailing divider
        //     coreAsWell: false // Whether core instance have this item on cxttap
        // },
        {
            id: 'cy-fit',
            content: 'fit view',
            tooltipText: 'Fits the nodes to the viewport',
            selector: cy,
            coreAsWell: true,
            onClickFunction: function () {cy.fit(cy.elements(':visible'));}
        },
        {
            id: 'rerun-lyt',
            content: 'rerun layout',
            tooltipText: 'Reruns current chosen layout',
//            image: {src : "add.svg", width : 12, height : 12, x : 6, y : 4},
            selector: cy,
            coreAsWell: true,
            onClickFunction: function () {
                var lytname = $('#layout-selection label.active').attr('id').slice(0, -6);
                runLyt(cy, lytname);
            }
            
        },
        {
            id: 'hide',
            content: 'hide',
            tooltipText: 'hide',
            selector: 'node, edge',
            onClickFunction: function (event) {
                var target = event.target || event.cyTarget;
                target.hide();
            },
            disabled: false,
            hasTrailingDivider: true
        },
        {
            id: 'select-outgoers',
            content: 'select outgoers',
            selector: 'node',
            onClickFunction: function (event) {
                var target = event.target || event.cyTarget;
                target.select();
                target.outgoers().nodes().select();
            },
            disabled: false
        },
        {
            id: 'select-incomers',
            content: 'select incomers',
            selector: 'node',
            onClickFunction: function (event) {
                var target = event.target || event.cyTarget;
                target.select();
                target.incomers().nodes().select();
            },
            disabled: false
        },
        {
            id: 'select-successors',
            content: 'select successors',
            selector: 'node',
            onClickFunction: function (event) {
                var target = event.target || event.cyTarget;
                target.select();
                target.successors().nodes().select();
            },
            disabled: false
        },
        {
            id: 'select-predecessors',
            content: 'select predecessors',
            selector: 'node',
            onClickFunction: function (event) {
                var target = event.target || event.cyTarget;
                target.select();
                target.predecessors().nodes().select();
            },
            disabled: false
        },

    ],
    // css classes that menu items will have
    menuItemClasses: [
        // add class names to this list
    ],
    // css classes that context menu will have
    contextMenuClasses: [
        // add class names to this list
    ]
};

function populateGeneInfo(geneId) {
    var ndata = cy.getElementById(geneId).data();
    $('#infoGeneName').html(ndata.nodesymbol);
    $('#infoGenePrefName').html(ndata.primname);
    $('#infoDef').html(ndata.desc);
    if (ndata.uniprot_id) {
        $('#uniprotLink').html(ndata.uniprot_id);
        $('#uniprotLink').attr("href", "http://www.uniprot.org/uniprot/"+ndata.uniprot_id);
    }
    else {$('#uniprotLink').html("");}
    if (ndata.ensembl_id){
        if (ndata.ensembl_id.length > 15) {
            $('#ensemblLink').html(ndata.ensembl_id.substring(0, 3) + '..' + ndata.ensembl_id.substr(-4));
        }
        else {
            $('#ensemblLink').html(ndata.ensembl_id);
        }
        var sp = (organism=="human")? "Homo_sapiens" : "Mus_musculus";
        $('#ensemblLink').attr("href", "http://www.ensembl.org/"+sp+"/Gene/Summary?db=core;g="+ndata.ensembl_id);
    }
    else {
        $('#ensemblLink').html("");
    };
    $('#genecardsLink').html(ndata.nodesymbol);
    $('#genecardsLink').attr("href", "http://www.genecards.org/cgi-bin/carddisp.pl?gene="+ndata.nodesymbol);
    $('#DICELink').html(ndata.nodesymbol);
    $('#DICELink').attr("href", "http://dice-database.org/genes/"+ndata.nodesymbol);
    $('#MGILink').html(ndata.mgi_id);
    $('#MGILink').attr("href", "http://www.informatics.jax.org/marker/"+ndata.id);
    
    if (ndata["expr:"+$("#celltype").val()] == null){
        $('#infoGeneExpr').html("?");
    }
    else {
        $('#infoGeneExpr').html(ndata["expr:"+$("#celltype").val()].toFixed(2));
    }
    var allTermsTable = "";
    if (ndata.allterms.length > 0) {
        ndata.allterms
             .sort(function(t1, t2) {return aspectPriority[t1.namespace]-aspectPriority[t2.namespace];})
             .forEach(function(term) {
                 var termref = goTermRefTemplate.replace("%TERMID", term.termid).replace("%LINKTEXT", term.termid);
                 allTermsTable += `<tr><td>${termref}</td><td>(${aspects[term.namespace]}) ${term.termname}</td></tr>`;
        });
    }
    else {allTermsTable += "<tr><td></td><td></td></tr>";}
    $('#infoAllAnnotations').html(allTermsTable);
    if (analysisType=="annot") {
        var slimTermsTable = "";
        if (ndata.slimterms.length > 0) {
            ndata.slimterms.forEach(function(term) {
                var termref = goTermRefTemplate.replace("%TERMID", term.termid).replace("%LINKTEXT", term.termid);
                slimTermsTable += `<tr><td>${termref}</td><td>(${aspects[term.namespace]}) ${term.termname}</td></tr>`;
            });
        }
        else {slimTermsTable += "<tr><td></td><td></td></tr>";}
        $('#infoSlimmedAnnotations').html(slimTermsTable);
    }
}

function side_panel(cy) {
    cy.on('tap', function(evt) {
        tapEvent = evt;
        var evtTarget = evt.target;
        if (evtTarget == cy) {
            $('#terminfo').hide();
            $('#edgeinfo').hide();
            $('#geneinfo').hide();
        }
        else if (evtTarget.group() == "nodes") {
            var node = evt.target;
            var ndata = node.data();
            currentSelectedGene = ndata.name;
            if (ndata.nodetype=="gene") {
                $('#terminfo').hide();
                $('#edgeinfo').hide();
                $('#geneinfo').show();
                populateGeneInfo(ndata.id);
            }
            else if (ndata.nodetype=="GOterm") {
                $('#terminfo').show();
                $('#edgeinfo').hide();
                $('#geneinfo').hide();
                $('#infoTermID').html(goTermRefTemplate.replace("%TERMID", ndata.name)
                                      .replace("%LINKTEXT", ndata.name));
                $('#infoTermDefinition').html(ndata.nodesymbol);
                $('#infoTermTotalGenes').html(ndata.tot_gn);
                if (analysisType=="enrich") {
                    $('#infoTermPval').html(ndata.P.toExponential(1));
                    $('#infoTermPvalAdj').html(ndata.Padj.toExponential(1));
                }
                var genePills = ndata.xgenes.map(function(g){
                    return genePillTemplate.replace('GENEID', g)
                        .replace('GENESYMBOL', cy.getElementById(g).data('nodesymbol'));
                });
                $('#infoTermXgenes').html(genePills.join(' '));
                $('#infoTermNXgenes').html(ndata.xgenes.length);
            }
        }
        else if (evtTarget.group() == "edges") {
            $('#terminfo').hide();
            $('#geneinfo').hide();
            $('#edgeinfo').show();
            var edgeDataTable = "";
            var specificTerms = evtTarget.data('specific_terms');
            for (var specificTerm in specificTerms) {
                var formattedRefs = specificTerms[specificTerm]['refs'].map(function(ref) {
                    var formattedSubRefs = ref.split("|").map(function(subref) {
                        if (subref.startsWith('PMID')) {
                            return pubmedLinkRefTemplate.replace('%PMID', subref.substr(5)).replace('%LINKTEXT', subref);
                        }
                        else if (subref.startsWith("MGI")) {
                            return mgiLinkRefTemplate.replace('%MGIID', subref.substr(4)).replace('%LINKTEXT', subref.substr(4));
                        }
                        else {
                            return subref;
                        }
                    });
                    return "<p class='my-0 small-font'>"+formattedSubRefs.join("|") +"</p>";
                });
                edgeDataTable += "<tr><td>"
                    +goTermRefTemplate.replace("%TERMID", specificTerm).replace("%LINKTEXT", specificTerm)
                    +"<br><p class='small-font'>"+specificTerms[specificTerm]['specific_term_name']
                    +"</p></td><td>"
                    +formattedRefs.join("")+"</td></tr>";
            }
            $('#edgedata').html(edgeDataTable);
            $('#relation').html(evtTarget.data('relation'));
        }
    });
}

function showParentNodes() {
    parentNodes.style({display:'element'});
    $("#rm_parent_nodes").html("Remove GO parents");
    parentsRemoved = false;
}

function hideParentNodes() {
    parentNodes.style({display:'none'});
    $("#rm_parent_nodes").html("Show GO parents");
    parentsRemoved = true;
}

function toggleShowParentNodes() {
    if (parentsRemoved) {
        showParentNodes();
    }
    else {
        hideParentNodes();
    }
}

function toggleShowGeneNodes() {
    var btn = $("#rm_gene_nodes");
    if (geneNodesRemoved) {
        geneNodes.style({display:'element'});
        $("#colorbar").show();
        btn.html("Remove gene nodes");
        geneNodesRemoved = false;
    }
    else {
        geneNodes.style({display:'none'});
        $("#colorbar").hide();
        btn.html("Show gene nodes");
        geneNodesRemoved = true;
    }
}

function _colorGenesUserSupplied() {
    var stile = cy.style();
    var minExprValue = cy.nodes("[nodetype='gene']").min(function(n){return n.data('expr:user_supplied');}).value;
    var maxExprValue = cy.nodes("[nodetype='gene']").max(function(n){return n.data('expr:user_supplied');}).value;
    var midExprValue;
    if ((minExprValue * maxExprValue) < 0) {
        maxExprValue = Math.max(Math.abs(minExprValue, maxExprValue));
        minExprValue = -maxExprValue;
        midExprValue = 0.0;
    }
    else {
        midExprValue = minExprValue + (maxExprValue - minExprValue)*0.5;
    }
    var geneColorScale = scaleSequential(interpolateRdYlBu).domain([maxExprValue, minExprValue]);
    cy.nodes("[nodetype='gene']").forEach(function (n) {
        var e = n.data('expr:user_supplied');
        if (isNaN(e)) {
            stile.selector('#'+n.id().replace(':', '\\:')+':unselected').style("background-color", 'rgb(255,255,255)');
        }
        else {
            stile.selector('#'+n.id().replace(':', '\\:')+':unselected').style("background-color", geneColorScale(e));
        }
    });
    stile.update();
    return {'min':minExprValue, 'mid':midExprValue, 'max':maxExprValue};
}

function _colorGenesExpr(ctp) {
    var stile = cy.style();
    var t = function(val){return Math.log10(val);};
    var t_1 = function(val){return Math.pow(10, val);};
    var geneColorScale = scaleSequential(interpolateRdYlBu).domain([t(100), t(0.8)]);
    cy.nodes("[nodetype='gene']").forEach(function (n) {
        var e = n.data('expr:'+ctp);
        if (isNaN(e)) {
            stile.selector('#'+n.id().replace(':', '\\:')+':unselected').style("background-color", 'rgb(255,255,255)');
        }
        else {
            stile.selector('#'+n.id().replace(':', '\\:')+':unselected').style("background-color", geneColorScale(t(Math.max(e, 1.0))));
        }
    });
    stile.update();
}

function colorGenesBy(colorOpt, callback) {
    if (colorOpt == 'default') {
        var stile = cy.style();
        stile.selector('node[nodetype="gene"]:unselected').style("background-color", '#f2a57b');
        stile.update();
        if (callback) {
            callback();
        }
    }
    else if (colorOpt == 'user_supplied') {
        var margins = _colorGenesUserSupplied();
        colorbar(margins['min'], margins['mid'], margins['max']);
        if (callback){
            callback();
        }
    }
    // Color by expression in a selected celltype
    else {
        $.getJSON(exprURL+colorOpt+'?callback=?', function(data) {
            cy.nodes("[nodetype='gene']").forEach(function(n) {
                n.data('expr:'+colorOpt, data[n.id()]);
            });
            var margins = _colorGenesExpr(colorOpt);
            colorbar(1.0, 10.0, 100.0);
            if (callback) {
                callback();
            }
        });
    }
};

function colorbar(m0, m1, m2) {
    d3selectAll('svg').remove();
        var colorbarWidth = 250;
        var txtHeight = 30;
        var colorbarHeight = 50;
        
        var bsvg = d3select('#colorbar').append("svg")
            .attr("height", colorbarHeight+txtHeight)
            .attr("width", colorbarWidth);
        
        var defs = bsvg.append("defs");
        var linearGradient = defs.append("linearGradient")
            .attr("id", "linear-gradient");
        var offsets = [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0];
        
        linearGradient.selectAll("stop")
            .data(offsets)
            .enter()
            .append("stop")
            .attr("offset", function(d){ return "" + (d*100) + "%"; })
            .attr("stop-color", function(d) { return interpolateRdYlBu(1.0 - d); });
        
        bsvg.append("rect")
            .attr("width", colorbarWidth)
            .attr("height", colorbarHeight)
            .style("fill", "url(#linear-gradient)");
        
        bsvg.append("text")
            .text(m0.toFixed(1))
            .attr("x", 0)
            .attr("y", colorbarHeight+20);
        
        bsvg.append("text")
            .text(m1.toFixed(1))
            .attr("x", colorbarWidth / 2)
            .attr("y", colorbarHeight+20)
            .attr("text-anchor", "middle");

        bsvg.append("text")
            .text(m2.toFixed(1))
            .attr("x", colorbarWidth)
            .attr("y", colorbarHeight+20)
            .attr("text-anchor", "end");
};

function colorizeNodes() {
    var stile = cy.style(cytoscapeStyle);
    if (analysisType=="enrich") {
        var minP = cy.nodes("[nodetype='GOterm']").min(function(n){
            var p=n.data('P');
            if (p>0) {
                return p;
            } else{
                return 1;
            }
        }).value;
        var maxP = cy.nodes("[nodetype='GOterm']").max(function(n){return n.data('P');}).value;
        var logScl = scaleLog().domain([minP, maxP]).range([0.65, 0.1]).clamp(true);
        var termColorScl = scaleSequential(interpolateBuGn);
        cy.nodes("[nodetype='GOterm']").forEach(function (n) {
            stile.selector('#'+n.id().replace(':', '\\:')+':unselected').style("background-color", termColorScl(logScl(n.data('P'))));
        });
    }
    else if (analysisType=="annot") {
        cy.nodes("[nodetype='GOterm']").forEach(function (n) {
            n.addClass('noColorData');
        });
    }
    stile.update();
    var fcGiven = cy.nodes('[nodetype="gene"]').map(function(n){return !isNaN(n.data('expr:user_supplied'));})
        .reduce(function(total, curValue){return total += curValue;}, 0);
    if (fcGiven > 0) {
        $("#celltype").val("user_supplied");
        colorGenesBy($("#celltype").val());
        $("#celltypeTable").html("["+$("#celltype option:selected").text()+"]");
    }
    else if (fcGiven==0){
        colorGenesBy("default");
    }
}

function addIcons() {
    $("img#uniprot-ico").attr("src", uniprotIcon);
    $("img#ensembl-ico").attr("src", ensemblIcon);
    $("img#dice-ico").attr("src", diceIcon);
    $("img#mgi-ico").attr("src", mgiIcon);
    $("img#genecards-ico").attr("src", genecardsIcon);
}

// Main function initializing the graph
$(document).ready(function() {
    cy = cytoscape({
        container: document.getElementById('cy') // container to render in
    });
    var cMenuInstance = cy.contextMenus(contextMenuOptions);
    var n;
    window.cy = cy;
    $("img#rendering-spinner").attr("src", spinnerIcon);
    $.getJSON(netURL+'?callback=?', function (data) {
        cy.json(data);
        defaultEdges = data.elements.edges;
        // Find parental GO term nodes and their edges
        parentNodes = cy.nodes("[genes_connected=0]");
        parentNodes = parentNodes.add(parentNodes.connectedEdges());
        // Find gene nodes and their edges
        geneNodes = cy.nodes("[nodetype='gene']");
        geneNodes = geneNodes.add(geneNodes.connectedEdges());
        window.geneNodes = geneNodes;
        // Find term nodes
        termNodes = cy.nodes("[nodetype='GOterm']");
        window.termNodes = termNodes;
        if ((analysisType=="enrich") && (termNodes.length==0)) { // there are only gene nodes
            colorizeNodes();
            addIcons();
            runLyt(cy, "cose").then(function(){
                cy.fit(cy.elements(':visible'));
                $('#nothingIsEnrichedWarn').modal();
            });
        }
        else {
            if (analysisType=="enrich") {
                var pvals = termNodes.map(function(n){return n.data('P');});
                var thrs = createBinThresholds(pvals, 5);
                thrs.reverse();
                thrs.forEach(function(thr, i) {
                    var optionHTML = '<option value='+thr+'>&#8804; '+thr.toExponential(2)+'</option>';
                    $('#pval_threshold').append(optionHTML);
                });
            }
            var largestComp = cy.elements().components().sort(function(a,b){return b.length-a.length;})[0];
            var nofTerms = largestComp.nodes('[nodetype="GOterm"]').length;
            var nofGenes = largestComp.nodes('[nodetype="gene"]').length;
            var ambiguousGenes = geneNodes.nodes().filter(function(n){return n.data('ambiguous');});
            var unrecognizedGenes = geneNodes.nodes().filter(function(n){return !n.data('identified');});
            var manyNodesThreshold = 150;
            if ((nofTerms<manyNodesThreshold) && (nofGenes<manyNodesThreshold)
                && (ambiguousGenes.length==0) && (unrecognizedGenes.length == 0)) {
                runLyt(cy, "cose").then(function(){cy.fit(cy.elements(':visible'));});
                colorizeNodes();
                addIcons();
            }
            else {
                $("#nofGenes").html(nofGenes.toString());
                $("#nofGenesTotal").html(geneNodes.length.toString());
                $("#nofTerms").html(nofTerms.toString());
                $("#nofTermsTotal").html(termNodes.length.toString());
                if ((nofTerms>manyNodesThreshold) && (nofGenes>manyNodesThreshold)) {
                    if (analysisType=="enrich"){$("#manyTermsSuggestion").show();}
                    $("#manyGenesSuggestion").show();
                    $("#renderWarning").show();
                    toggleShowGeneNodes();
                }
                else if ((nofTerms<manyNodesThreshold) && (nofGenes>manyNodesThreshold)){
                    $("#manyGenesSuggestion").show();
                    $("#renderWarning").show();
                    toggleShowGeneNodes();
                }
                else if ((nofTerms>manyNodesThreshold) && (nofGenes<manyNodesThreshold)){
                    if (analysisType=="enrich"){$("#manyTermsSuggestion").show();}
                    $("#renderWarning").show();
                }
                if (unrecognizedGenes.length != 0) {
                    $("#unrecognizedGenesWarning").show();
                    var warnHTML = unrecognizedGenes.map(function(n){return n.data('nodesymbol');})
                        .slice(0, 2).join(', ');
                    if (unrecognizedGenes.length > 2) {
                        warnHTML += " and some others";
                    }
                    $("#unrecognizedGenes").html(warnHTML);
                }
                if (ambiguousGenes.length != 0) {
                    $("#ambiguousGenesWarning").show();
                    warnHTML = ambiguousGenes.map(function(n){return n.data('nodesymbol');})
                        .slice(0, 2).join(', ');
                    if (ambiguousGenes.length > 2) {
                        warnHTML += " and some others";
                    }
                    $("#ambiguousGenes").html(warnHTML);
                }
                $("#jobWarnings").modal();
                $("#renderNetCy").show();
            }
        }
    });
    // Add side panel functions
    side_panel(cy);

    // Add event listeners on some elements of the DOM
    $("#rm_parent_nodes").click(function () {
        toggleShowParentNodes();
    });
    
    $("#layout-selection").on('click', function(){
        window.setTimeout(function() {
            var lytname = $('#layout-selection label.active').attr('id').slice(0, -6);
            runLyt(cy, lytname);
        }, 200);
    });
    
    $("#fit_window").click(function() {
        cy.fit(cy.elements(':visible'));});
    $("#rm_gene_nodes").click(function () {
        toggleShowGeneNodes();
    });
    
    $("#hamburger").click(function(i){
        $("#side_panel_div").toggle();
        $("#cy").toggleClass("side-collapsed");
    });
    
    $(".exportCYJS").click(function(){
        var netJSON = JSON.stringify(cy.json());
        var txtBlob = new Blob([netJSON], {type: "text/plain;charset=utf-8"});
        FileSaver.saveAs( txtBlob, 'net.cyjs', true);
    });
    
    $("#export-png").click(function(){
        var b64key = 'base64,';
        imgContent = cy.png({"scale":2.0});
        var b64 = imgContent.substring(imgContent.indexOf(b64key) + b64key.length );
        var imgBlob = b64toBlob( b64, 'image/png' );
        FileSaver.saveAs( imgBlob, 'graph.png' );
    });
    
    $("#export-png-hidef").click(function(){
        var b64key = 'base64,';
        imgContent = cy.png({"scale":4.0});
        var b64 = imgContent.substring(imgContent.indexOf(b64key) + b64key.length );
        var imgBlob = b64toBlob( b64, 'image/png' );
        FileSaver.saveAs( imgBlob, 'graph.png' );
    });
    
    $("#export-jpg").click(function(){
        var b64key = 'base64,';
        imgContent = cy.jpg({"scale":2.0});
        var b64 = imgContent.substring(imgContent.indexOf(b64key) + b64key.length );
        var imgBlob = b64toBlob( b64, 'image/jpg' );
        FileSaver.saveAs( imgBlob, 'graph.jpg' );
    });

    $("#renderNet").one('click', function(evt, target){
        $("#renderNet").attr("disabled", true);
        $("#rendering-spinner").show();
        $("#renderNet").html("Computing...");
        $("#renderNetCy").hide();
        // $("#layout-selection label").each(function(){$(this).removeClass("active");});
        // $("#eulerLayout").addClass("active");
        runLyt(cy, "cose").then(function(){
            cy.fit(cy.elements(':visible'));
            $("#jobWarnings").modal('hide');});
        colorizeNodes();
        addIcons();
    });
    
    $("#renderNetCy").one('click', function(){
        $("#renderNetCy").attr("disabled", true);
        $("#renderNetCy").html("Computing...");
        $("#renderNetCy").hide();
        runLyt(cy, "cose").then(function(){cy.fit(cy.elements(':visible'));});
        colorizeNodes();
        addIcons();
    });
    
    $(document.body).on('click', '.genePill', function(event){
        var geneId = event.target.getAttribute('id').substring(1);
        cy.nodes('[nodetype="gene"]').unselect();
        cy.getElementById(geneId).select();
        populateGeneInfo(geneId);
        $('#geneinfo').show();
    });
    
    $("#celltype").change(function() {
        var colorOpt = $(this).val();
        colorGenesBy(colorOpt);
        if (colorOpt != "default") {
            $("#celltypeTable").html("["+$("#celltype option:selected").text()+"]");
            var e = cy.nodes('[name="'+currentSelectedGene+'"]').data('expr:'+celltype);
            if (e == null) {
                $('#infoGeneExpr').html("?");
            }
            else {
                $('#infoGeneExpr').html(e.toFixed(2));
            }
        }
        if (colorOpt == "default" || colorOpt == "user_supplied") {
            $("#tpmFlag").hide();
        }
        else {$("#tpmFlag").show();}
    });
    $("#celltype").trigger("change");
    
    $("#pval_threshold").change(function() {
        // Returning to default state
        showParentNodes();
        cy.edges().remove();
        cy.add(defaultEdges);
        termNodes.style({display:'element'});
        var thr = Number($(this).val());
        var nodesToHide = termNodes.filter(function(n) {return n.data('P')>thr;});
        var edgesModified = graphutils.hideNodes(cy, nodesToHide);
    });

    $("#nodeNamingSelector").change(function(evt){
        var naming = $("input[name='nodeNaming']:checked").val();
        if (naming=="pref_symbols") {
            cy.style().selector("node[nodetype='gene']").style("label", "data(primname)").update();
        }
        else if (naming=="as_input") {
            cy.style().selector("node[nodetype='gene']").style("label", "data(nodesymbol)").update();
        };
    });
});
