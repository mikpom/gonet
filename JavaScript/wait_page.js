var $ =  require("jquery");
require("expose-loader?$!jquery");
require("expose-loader?jQuery!jquery");

function checkStatus(){
    window.setTimeout(function(){
        $("#loading-badge").show();
        window.setTimeout(function(){
            $.ajax(statusURL).done(function(resp) {
                $("#loading-badge").hide();
                if (resp.status == 'ready') {
                    location.reload();
                }
                else {
                    checkStatus();
                }
            });

        }, 1000);
    }, 5000);
}
$(document).ready(function(){
    $('#progress-url').html(location.toString());
});

checkStatus();


