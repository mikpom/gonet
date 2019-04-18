var $ = require("jquery");
require("expose-loader?$!jquery");
require("expose-loader?jQuery!jquery");
import 'bootstrap';

var sampdata = ["CCR4	5.38", "CCR6	5.22", "ZNRF1	2.93", "IL17RE	4.75",
                "IL1R1	5.22", "HLF	3.64", "CNTNAP1	4.26", "TANC1	4.19",
                "COL5A1	4.45", "RORC	4.17", "SLC35G1	2.12", "PTPN13	4.20",
                "ZC2HC1A	2.69", "NTRK2	4.56", "ADAM12	4.34", "HRH4	4.25",
                "FNBP1L	2.24", "AIRE	4.05", "ELOVL4	3.55", "MGLL	3.32",
                "MYO7A	3.57", "SEMA5A	3.66", "CHDH	3.92", "CTSH	3.08",
                "LINGO4	3.69", "SLC22A3	3.74", "MATN2	3.69", "IL17RB	3.85",
                "FRY	2.46", "ANK1	2.69", "COL5A3	3.49", "MCAM	2.58",
                "SEMA3G	3.08", "RNF182	3.48", "LAMA2	2.33", "NR1D1	2.28",
                "NXN	2.84", "HSD11B1	2.98", "CASR	3.26", 
                "CC2D2A	2.79", "MCF2L2	2.01", "TRIQK	2.60", "ZNF462	2.72",
                "IL9R	2.65", "FAM124B	2.50", "IL2	2.53", "FANK1	2.64",
                "PLD1	2.93", "FSBP	2.18", "LTK	2.85", "SEPT10	2.12",
                "PANK1	2.13", "C15orf53	2.08", "PPARG	2.79", "IL23R	2.68",
                "MAPK10	2.66", "HACD1	2.11", "NMU	2.59", "L1CAM	2.35",
                "IL17A	2.62", "FAM189A2	2.58", "IRAK3	2.17", "CRISPLD2	2.15",
                "DMD	2.33", "HOMER3	2.13", "CAVIN1	2.29"].join('\n');

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
    $("#popoverbutton").popover({title:$("#bg-popover-title").html(),
                                 content:$("#bg-popover-content").html(), 
                                 html:true});
    $("#popoverbutton").on('inserted.bs.popover', function() {
        $("#bg-popover-dismiss").on("click", function() {
            $("#popoverbutton").popover('hide');
        });
    });
    
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

    $("#reset-btn").click(function() {
        $("#input-form").get(0).reset();
        updateAnalysisType();
        updateSlimType();
        updateBgType();
        updateOrganism();
    });
    
    updateAnalysisType();
    updateSlimType();
    updateBgType();
    updateOrganism();
});

