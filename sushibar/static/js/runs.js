const TRELLO_REGEX = /^https{0,1}:\/\/trello.com\/c\/([0-9A-Za-z]{8})\/[^\/]*$/;

function format_date(run) {
  return moment(run["created_at"]).format("MMM D");
}

function get_dataset(resource, idx, data) {
  // Bottle Rocket and Castello Cavalcanti.
  var colors = ["#F3BE1A", "#AC9DBC", "#067586", "#C87533", "#52656B", "#CF5351", "#2196F3", "#738F1E", "#66321C", "#FFA475"];

  return {
    label: resource,
    data: data.map(function(x) {
      return x.resource_counts[resource] || 0;
    }),
    backgroundColor: Chart.helpers.color(colors[idx]).alpha(0.5).rgbString(),
    borderColor: colors[idx],
    borderWidth: 1,
    fill: false,
    pointRadius: 5
  }
}

function create_config(data) {
  if (!data.length) { return; }
  var counts = data[0].resource_counts;
  delete counts['total']
  delete counts['json']

  return {
    type: 'line',
    data: {
      labels: data.map(format_date),
      datasets: Object.keys(counts).map(
        function(x, i) {
          return get_dataset(x, i, data);
        }),
    },
    options: {
      responsive: true,
      legend: {
        position: 'top',
      },
      scales: {
        xAxes: [{
          display: true,
          scaleLabel: {
            display: true,
            labelString: 'Date',
            fontSize: 16,
          }
        }],
        yAxes: [{
          display: true,
          scaleLabel: {
            display: true,
            labelString: 'Count',
            fontSize: 16
          }
        }]
      },
      title: {
        display: true,
        text: 'Resource Counts',
        fontSize: 20,
        padding: 10
      }
    }
  };
}




/****************** TRELLO API FUNCTIONS ******************/


  function update_trello_link(el) {
    $(".trello-alert").css("display", "none");
    var url = $("#trello-link-input").val().trim();
    $("#trello-invalid-url").css('visibility', 'hidden');
    if(TRELLO_REGEX.test(url)){
      $("#submit-trello-link").removeClass("disabled").removeAttr('disabled');
      $(".trello-link").attr('href', url);
    } else {
      $("#submit-trello-link").addClass("disabled").attr('disabled', 'disabled');
      $(".trello-link").attr('href', '#');
      url && $("#trello-invalid-url").css('visibility', 'visible');
    }
  }

  function trello_submit_url(){
    trello_pending();
    var trello_url = $("#trello-link-input").val().trim();
    var save_trello_url = "/services/trello/" + channel_id + "/save_trello_url/";
    $.ajax({
      url: save_trello_url,
      type: "POST",
      data: {"trello_url": trello_url},
      success: function(data){
        $("#trello-embed-wrapper").html("");
        $("#trello-options, #trello-embed").removeClass("hidden");
        $("#trello-url-prompt, #trello-link-wrapper").addClass("hidden");
        window.TrelloCards.create(trello_url, $("#trello-embed-wrapper")[0], { compact: true  });
        $(".trello-card-alert").addClass("hidden");
        $(".trello-action-alert").removeClass("hidden");
        trello_success("Trello card added!");
      },
      error: trello_error
    });
  }

  function trello_remove_url(){
    if(confirm("Are you sure you want to remove this URL?")) {
      trello_pending();
      var save_trello_url = "/services/trello/" + channel_id + "/save_trello_url/";
      $.ajax({
        url: save_trello_url,
        type: "POST",
        data: {"trello_url": ""},
        success: function(data){
          $("#trello-link-input").val("");
          $("#trello-embed").addClass("hidden");
          $("#trello-url-prompt, #trello-link-wrapper").removeClass("hidden");
          $(".trello-card-alert").removeClass("hidden");
          $(".trello-action-alert").addClass("hidden");
          trello_success("Removed Trello URL");
        },
        error: trello_error
      });
    }
  }

  function trello_edit_url(el) {
    $(".trello-alert").css("display", "none");
    $("#trello-options").addClass("hidden");
    $("#trello-link-wrapper").removeClass("hidden");
    $("#trello-comment-section").collapse('hide');
    update_trello_link(el);
  }

  function trello_error(message) {
    $(".trello-alert").css("display", "none");
    $("#trello-error").css("display", "block");
    $("#trello-error .text").text(message.responseText);
  }
  function trello_success(message) {
    $(".trello-alert").css("display", "none");
    $("#trello-success").css("display", "block").text(message);
    setTimeout(function() {
      $("#trello-success").fadeOut(500);
    }, 3000);
  }
  function trello_pending() {
    $(".trello-alert").css("display", "none");
    $("#trello-pending").css("display", "block");
  }

  function trello_add_checklist_item(item, success_message) {
    trello_pending();
    var add_item_url = "/services/trello/" + channel_id + "/add_item/";
    $.ajax({
      url: add_item_url,
      type: "POST",
      data: {"item": item},
      success: function(data) {
        trello_success(success_message);
      },
      error: trello_error
    });
  }

  function trello_move_card_to_list(endpoint, success_message, onpending, onsuccess, onerror) {
    onpending();
    $.ajax({
      url: "/services/trello/" + channel_id + "/" + endpoint + "/",
      type: "PUT",
      success: function(data) { onsuccess(success_message); },
      error: onerror
    });
  }

  function trello_flag_channel_for_qa() {
    trello_pending();
    $.ajax({
      url: "/api/channels/" + channel_id + "/flag_for_qa/",
      type: "POST",
      success: function(data) {
        trello_success("Flagged channel for QA");
        $("#feedback-link").attr("href", "https://docs.google.com/spreadsheets/d/" + data.qa_sheet_id);
        $("#feedback-embed").attr("src", "https://docs.google.com/a/learningequality.org/spreadsheets/d/" + data.qa_sheet_id + "/htmlembed")
        $("#feedback-embed-wrapper").removeClass("hidden");
        $("#feedback-prompt-wrapper").addClass("hidden");
        history.replaceState(undefined, undefined, "#feedback");
        $('.nav-link[href="#feedback"]').tab('show');
      },
      error: trello_error
    });
  }

  function trello_flag_channel_for_publish() {
    trello_move_card_to_list("flag_for_publish", "Sent publish request", trello_pending, trello_success, trello_error);
  }

  function alert_trello_error(message) {
    $("#alert-area .alert").addClass("hidden");
    $(".trello-action-error").removeClass("hidden").text(message.responseText);
    setTimeout(function() {
      $(".trello-action-error").addClass("hidden");
      $(".alert-processing, .alert-prompt").toggleClass("hidden");
      $(".trello-action-alert").removeClass("hidden");
    }, 4000);
  }

  function alert_trello_success(message) {
    $("#alert-area .alert").addClass("hidden");
    $(".trello-action-success").removeClass("hidden");
    $(".trello-action-success .text").text(message);
    setTimeout(function() {
      $(".trello-action-success").addClass("hidden");
    }, 3000);
  }

  function alert_trello_pending(message) {
    $(".alert-processing, .alert-prompt").toggleClass("hidden");
  }

  function alert_trello_done() {
    trello_move_card_to_list("mark_as_done", "Marked channel as done", alert_trello_pending, alert_trello_success, alert_trello_error);
  }

  function alert_trello_qa() {
    trello_move_card_to_list("flag_for_qa", "Flagged channel for QA", alert_trello_pending, alert_trello_success, alert_trello_error);
  }

  function alert_trello_publish() {
    trello_move_card_to_list("flag_for_publish", "Sent publish request", alert_trello_pending, alert_trello_success, alert_trello_error);
  }

  function update_trello_comment() {
    $("#trello-invalid-comment").css('visibility', 'hidden');
  }

  function trello_send_comment() {
    if(!$("#trello-comment").val().trim()) {
      $("#trello-invalid-comment").css('visibility', 'visible');
    } else {
      $(".trello-alert").css("display", "none");
      $("#trello-comment-sending").css("display", "block");
      var comment_url = "/services/trello/" + channel_id + "/send_comment/";
      $.ajax({
        url: comment_url,
        type: "POST",
        data: {"comment": $("#trello-comment").val().trim()},
        success: function(data) {
          $("#trello-comment-section").collapse('hide');
          $("#trello-comment").val("");
          trello_success("Comment Sent!");
        },
        error: function(message) {
          $(".trello-alert").css("display", "none");
          $("#trello-comment-error").css("display", "block");
          $("#trello-comment-error .text").text(message.responseText);
        }
      });
    }
  }


/****************** END TRELLO API FUNCITONS ******************/



$(function() {
  // TODO: Add .card-action class once Bootstrap error "Tooltip is transitioning" is fixed
  // https://github.com/twbs/bootstrap/issues/21607
  $('.stage-progress, .channel-id-btn').tooltip();

  var clipboard = new Clipboard('.channel-id-btn');
  $(document).on('shown.bs.tooltip', function (e) {
    if($(e.target).hasClass('channel-id-btn')) {
      setTimeout(function () {
        $(e.target).tooltip('hide');
      }, 1000);
    }
  });

  // channel save functionality
  var toggleSave = function(data) {
    $('.save-icon').toggleClass('fa-star');
    $('.save-icon').toggleClass('fa-star-o');
  };
  $('.save-icon').click(function() {
    var save_channel_url = "/api/channels/" + channel_id + "/save_to_profile/";
    if ($(this).hasClass('fa-star')) {
      // Unfollow this channel.
      $.post(save_channel_url, {"save_channel_to_profile": false}, toggleSave);
    } else {
      // Follow this channel.
      $.post(save_channel_url, {"save_channel_to_profile": true}, toggleSave);
      // TODO: check if successful (what if user not logged in? redirect to login page?)
    }
  });

  if (!$("#channel-run").hasClass("new-channel")) {
    // Get chart data.
    $.getJSON("/api/channels/" + channel_id + "/runs/", function(data) {
      var myLineChart = new Chart(
        $("#resource-chart")[0].getContext('2d'),
        create_config(
          data.filter(function(x) {
            return x.resource_counts !== undefined && x.resource_counts !== null;
          }).slice(0, 10)));
    });
    // Collapse content tree.
    $('.content-tree > li a').click(function() {
      $(this).parent().find('ul').slideToggle(100);
    });


    var hash = window.location.hash || "#summary";
    history.replaceState(undefined, undefined, hash);
    $('.nav-link[href="' + hash + '"]').tab('show');

    $('.nav-link').click(function(e) {
      var new_hash = this['href'].substring(this['href'].indexOf('#')+1);
      history.replaceState(undefined, undefined, "#" + new_hash);
    });
  }


  $("#trello-link-input").on("keyup", update_trello_link);
  $("#trello-link-input").on("keydown", update_trello_link);
  $("#trello-link-input").on("paste", update_trello_link);

  $("#submit-trello-link").on("click", trello_submit_url);
  $("#trello-link-edit").on("click", trello_edit_url);
  $("#remove-trello-link").on("click", trello_remove_url);
  $("#trello-link-qa").on("click", trello_flag_channel_for_qa);
  $("#trello-link-publish").on("click", trello_flag_channel_for_publish);
  $("#trello-link-storage").on("click", function() {
    var message = "Increase storage for " + request_storage_email;
    trello_add_checklist_item(message, "Sent request for storage");
  });
  $("#trello-send-comment").on("click", trello_send_comment);
  $("#trello-comment").on("keyup", update_trello_comment);
  $("#trello-comment").on("keydown", update_trello_comment);
  $("#trello-comment").on("paste", update_trello_comment);
  $(".trello-alert-mark-done").on("click", alert_trello_done);
  $(".trello-alert-flag-for-qa").on("click", alert_trello_qa);
  $(".trello-alert-request-publish").on("click", alert_trello_publish);

  $("#refresh-feedback-embed").on("click", function() {
    $("#feedback-embed").attr('src', $("#feedback-embed").attr('src'));
  });
});
