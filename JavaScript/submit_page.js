var $ = require("jquery");
require("expose-loader?$!jquery");
require("expose-loader?jQuery!jquery");
import 'bootstrap';

var sampdata = ["ABCB1	0.6", "AK5	-0.54", "AMZ2P1	-0.65",
                "APOBR	0.53", "BHLHE40	0.51", "CCDC75	0.52",
                "CCL20	0.53", "CCR7	-0.59", "CDCA7L	-0.69",
                "CDK11B	0.52", "CMIP	0.51", "DAB1	0.51",
                "DENND3	0.53", "EDAR	-0.51", "EGLN3	0.52",
                "ERF	0.53", "ESR2	0.56", "FKBP5	-0.69",
                "FLVCR1-AS1	-0.53", "FOXP4	0.53", "FRY	0.63",
                "GPA33	-0.77", "HAVCR2	-0.59", "HIST1H1B	0.7",
                "HIST1H1C	0.9", "HIST1H1D	0.74", "HIST1H1E	0.85",
                "HIST1H2AG	0.64", "HIST1H2AH	0.59", "HIST1H2AM	0.53",
                "HIST1H2BC	0.62", "HIST2H2AC	0.79", "HIST2H2BC	0.53",
                "IER5	0.54", "IFFO2	0.52", "JUN	0.65",
                "KIF5C	0.6", "KIT	0.57", "LOC100130992	0.55",
                "LOC387895	0.52", "LOC729041	0.59", "LPAR3	0.56",
                "LPPR2	0.51", "LTC4S	0.67", "LTK	0.81",
                "MACF1	0.5", "MARCH3	-0.6", "MMP25	0.52",
                "MYBL1	0.53", "NOG	-0.73", "PDE7B	-0.51",
                "PHGDH	-0.56", "PHLDA3	0.51", "PIK3IP1	-0.56",
                "PLCB1	0.5", "PLXNA3	0.55", "PTPN13	0.67",
                "PVRL3	0.64", "RHEBL1	0.52", "RPL19P12	0.55",
                "SLA	-0.5", "SMAD7	0.52", "ST6GALNAC1	-0.55",
                "SYTL2	0.56", "TMOD2	0.6", "TXK	-0.52",
                "ZNF225	-0.51", "ZNF256	-0.51", "ZNF618	-0.55",
                "ZNF761	-0.53"].join('\n');

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

