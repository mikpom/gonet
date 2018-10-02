var $ = require("jquery");
require("expose-loader?$!jquery");
require("expose-loader?jQuery!jquery");

var sampdata = "ABCB1	0.6\nAK5	-0.54\nAMZ2P1	-0.65\nAPOBR	0.53\nBHLHE40	0.51\nCCDC75	0.52\nCCL20	0.53\nCCR7	-0.59\nCDCA7L	-0.69\nCDK11B	0.52\nCMIP	0.51\nDAB1	0.51\nDENND3	0.53\nEDAR	-0.51\nEGLN3	0.52\nERF	0.53\nESR2	0.56\nFKBP5	-0.69\nFLVCR1-AS1	-0.53\nFOXP4	0.53\nFRY	0.63\nGPA33	-0.77\nHAVCR2	-0.59\nHIST1H1B	0.7\nHIST1H1C	0.9\nHIST1H1D	0.74\nHIST1H1E	0.85\nHIST1H2AG	0.64\nHIST1H2AH	0.59\nHIST1H2AM	0.53\nHIST1H2BC	0.62\nHIST2H2AC	0.79\nHIST2H2BC	0.53\nIER5	0.54\nIFFO2	0.52\nJUN	0.65\nKIF5C	0.6\nKIT	0.57\nLOC100130992	0.55\nLOC387895	0.52\nLOC729041	0.59\nLPAR3	0.56\nLPPR2	0.51\nLTC4S	0.67\nLTK	0.81\nMACF1	0.5\nMARCH3	-0.6\nMMP25	0.52\nMYBL1	0.53\nNOG	-0.73\nPDE7B	-0.51\nPHGDH	-0.56\nPHLDA3	0.51\nPIK3IP1	-0.56\nPLCB1	0.5\nPLXNA3	0.55\nPTPN13	0.67\nPVRL3	0.64\nRHEBL1	0.52\nRPL19P12	0.55\nSLA	-0.5\nSMAD7	0.52\nST6GALNAC1	-0.55\nSYTL2	0.56\nTMOD2	0.6\nTXK	-0.52\nZNF225	-0.51\nZNF256	-0.51\nZNF618	-0.55\nZNF761	-0.53";


function updateAnalysisType() {
    var analysisType = $("#analysis_type input").filter(function(i, e){return $(e).prop("checked");}).val();
    var enrichEleIds = ["id_qvalue", "id_bg_type", "id_bg_cell", "id_bg_file"];
    var annotEleIds  = ["id_slim", "id_custom_terms"];
    if (analysisType == "enrich") {
        annotEleIds.forEach(function(eleId) {
            $("#"+eleId).attr("disabled", "");
        });
        enrichEleIds.forEach(function(eleId) {
            $("#"+eleId).removeAttr("disabled");
        });
    }
    else if (analysisType == "annot") {
        enrichEleIds.forEach(function(eleId) {
            $("#"+eleId).attr("disabled", "");
        });
        annotEleIds.forEach(function(eleId) {
            $("#"+eleId).removeAttr("disabled");
        });
    }
    return analysisType;
}

function updateSlimType() {
    var slimType = $("#id_slim").val();
    if (slimType=="custom") {
        $("#custom_terms_row").show();
        $("#id_namespace").attr("disabled", "");
        $("#annot_param textarea").animate({"max-height":"400px"});
        $(".custom-terms-expand").animate({"max-height":"400px"});
    }
    else {
        $("#custom_terms_row").hide();
        $("#annot_param textarea").animate({"max-height":"10px"});
        $(".custom-terms-expand").animate({"max-height":"10px"});
        $("#id_namespace").removeAttr("disabled");
    }
}

function updateBgType() {
    var bgType = $("#id_bg_type").val();
    if (bgType == "all") {
        $("#predef_bg_row").hide();
        $("#custom_bg_row").hide();
    }
    else if (bgType == "custom") {
        $("#predef_bg_row").hide();
        $("#custom_bg_row").show();
    }
    else if (bgType == "predef") {
        $("#predef_bg_row").show();
        $("#custom_bg_row").hide();
    }
}

function updateOrganism() {
    var organism = $("#organism input").filter(function(i, e){return $(e).prop("checked");}).val();
    window.organism = organism;
    var humanBgOptions = $("#predef_bg_row option").filter(function(i, e){return $(e).html().includes("DICE") || $(e).html().includes("HPA");});
    var mouseBgOptions = $("#predef_bg_row option").filter(function(i, e){return $(e).html().includes("Bgee");});
    window.humanBgOptions = humanBgOptions;
    window.mouseBgOptions = mouseBgOptions;
    if (organism == "mouse") {
        humanBgOptions.hide();
        mouseBgOptions.show();
        $("#id_bg_cell").val(mouseBgOptions[0].value);
    }
    else if (organism == "human") {
        humanBgOptions.show();
        mouseBgOptions.hide();
        $("#id_bg_cell").val(humanBgOptions[0].value);
    }

}

$(document).ready(function() {
    $("#samp_data_button").click(function(){
        $("#id_paste_data").val(sampdata);
        $("#id_organism").val("human");
    });
    $("#analysis_type").on("change", function(evt) {
        updateAnalysisType();
    });
    $("#id_slim").on("change", function() {
        updateSlimType();
    });
    $("#id_bg_type").on("change", function() {
        updateBgType();
    });
    $("#organism").on("change", function() {
        updateOrganism();
    });
    
    var analysisType = updateAnalysisType();
    updateSlimType();
    updateBgType();
    updateOrganism();
});

