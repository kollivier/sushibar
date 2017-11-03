const TRELLO_API_KEY = "d8f67a223292cb8b4b78700405e0c9f3";
const TRELLO_TOKEN = "054415d8530c5680761ccfe37898d8110c1906a16c418b372f1965217bc5c1e0";
const TRELLO_REGEX = /https{0,1}:\/\/trello.com\/c\/([0-9A-Za-z]{8})\/.*/;
const TRELLO_BOARD = "59f104b79ba77c02bcf8d9e4"; // when ready: 58b4a93607f1148a4b697899;

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
    $(".trello-pending").css("display", "block");
    var trello_url = $("#trello-link-input").val().trim();
    var save_trello_url = "/services/trello/" + channel_id + "/save_trello_url/";
    $.ajax({
      url: save_trello_url,
      type: "POST",
      data: {"trello_url": trello_url},
      success: function(data){
        $("#trello-link-input").attr('readonly', 'readonly');
        $("#submit-trello-link").addClass("hidden");
        $("#edit-trello-link, #remove-trello-link").removeClass("hidden");
        $(".trello-action").removeClass("disabled").removeAttr('disabled');
      },
      error: trello_error
    });
  }

  function trello_remove_url(){
    $(".trello-alert").css("display", "none");
    $(".trello-pending").css("display", "block");
    var save_trello_url = "/services/trello/" + channel_id + "/save_trello_url/";
    $.ajax({
      url: save_trello_url,
      type: "POST",
      data: {"trello_url": ""},
      success: function(data){
        $("#trello-link-input").removeAttr('readonly').val("");
            $("#submit-trello-link").removeClass("hidden");
            $("#edit-trello-link, #remove-trello-link").addClass("hidden");
            $(".trello-action").addClass("disabled").attr('disabled', 'disabled');
      },
      error: trello_error
    });
  }

  function trello_edit_url(el) {
    $(".trello-alert").css("display", "none");
    $("#edit-trello-link, #remove-trello-link").addClass("hidden");
    $("#submit-trello-link").removeClass("hidden");
    $("#trello-link-input").removeAttr('readonly');
    $(".trello-action").addClass("disabled").attr('disabled', 'disabled');
    update_trello_link(el);
  }

  function trello_error(message) {
    $(".trello-pending").css("display", "none");
    $(".trello-error").css("display", "block").text(message.responseText);
  }
  function trello_success(message) {
    $(".trello-pending").css("display", "none");
    $(".trello-success").css("display", "block").text(message);
  }

  function trello_add_checklist_item(item, success_message) {
    $(".trello-alert").css("display", "none");
    $(".trello-pending").css("display", "block");
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

/****************** END TRELLO API FUNCITONS ******************/



$(function() {
  $('.stage-progress').tooltip();

  var clipboard = new Clipboard('.channel-id-btn');
  $('.channel-id-btn').tooltip();
  $(document).on('shown.bs.tooltip', function (e) {
    setTimeout(function () {
      $(e.target).tooltip('hide');
    }, 500);
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


  var hash = window.location.hash;
  hash && $('.nav-link[href="' + hash + '"]').tab('show');

  $('.nav-link').click(function(e) {
    var new_hash = this['href'].substring(this['href'].indexOf('#')+1);
    history.replaceState(undefined, undefined, "#" + new_hash);
  });

  $("#trello-link-input").on("keyup", update_trello_link);
  $("#trello-link-input").on("keydown", update_trello_link);
  $("#trello-link-input").on("paste", update_trello_link);
  $("#submit-trello-link").on("click", trello_submit_url);
  $("#edit-trello-link ").on("click", trello_edit_url);
  $("#remove-trello-link ").on("click", trello_remove_url);
  $(".trello-link-qa").on("click", function() {
    trello_add_checklist_item("QA channel", "Flagged channel for QA");
  });
  $(".trello-link-storage").on("click", function() {
    var message = "Increase storage for " + user_email;
    trello_add_checklist_item(message, "Sent request for storage");
  });
});
