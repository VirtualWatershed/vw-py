/**
 * The code to append each new county to our list of counties
 */
$(function() {
  // search for a model_run_name from the associated virtual watershed
  $('#search').click(function () {
    var model_run_name = $("#model_run_name").val();
      window.location.href = "/search?model_run_name=" + model_run_name; 
    }
  );
});
