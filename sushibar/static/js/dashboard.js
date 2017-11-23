// TODO: expose this in every view as part of header.
$(function() {
  var clipboard = new Clipboard('.channel-id-btn');
  $('.popover-icon').tooltip();
  $(document).on('shown.bs.tooltip', function (e) {
    if($(e.target).hasClass('channel-id-btn')) {
      setTimeout(function () {
        $(e.target).tooltip('hide');
      }, 1000);
    }
  });

  var start_channel_handler = function (channel_id) {

      var toggleRestartButton = function () {
          button_el = $('*[data-target="#restart-'+channel_id+'-modal"]');
          // TODO: change icon to indicate it's running...
      }

      // build URL for control endpoint
      var channel_control_url = "/api/channels/" + channel_id + "/control/";

      // extract args from modaal's checkboxes state
      var cur_modal = $('div.action-modal.show');  // get the modal for current channel
      post_data = {
        "command": "start",
        "args": JSON.stringify({
          update: cur_modal.find('input#update-run-option').get(0).checked,
          stage: cur_modal.find('input#stage-run').get(0).checked,
          publish: cur_modal.find('input#publish-run').get(0).checked
        }),
        "options": JSON.stringify({})
      }
      $.post(channel_control_url, post_data, toggleRestartButton);

      // close modal
      $('#restart-'+channel_id+'-modal').modal('hide');
  }

  // HACK: attach to window so it's globally accessible
  window.start_channel_handler = start_channel_handler;

  $(".filter").on("change", function(event) {
    var matches = $("." + ($(this).val() || "channel-row"));
    $(".channel-row").css("display", "none");
    matches.css("display", "block");
    update_channel_count();
  });

  $('#create-channel-form').on('submit', function(event) {
    event.preventDefault();
    $("#channel-register-error").css("display", "none");
    $('#create-channel-button').attr("disabled", "disabled");
    $.ajax({
        type: $(this).attr('method'),
        url: this.action,
        data: $(this).serialize(),
        context: this,
        success: function(data) {
          data = JSON.parse(data);
          if(data.success) {
            window.location = data.redirect_url;
          } else {
            var form = $(data.html).find('#create-channel-form').html();
            $('#create-channel-form').html(form);
            $('#create-channel-form input, #create-channel-button').removeAttr("disabled");
          }
        }, error: function(data) {
          $("#channel-register-error").text(data.responseText).css("display", "block");
          $('#create-channel-form input, #create-channel-button').removeAttr("disabled");
        }
    });
  });

  $(".delete-new-channel").on('click', function() {
    if(confirm("Are you sure you want to delete channel " + $(this).data('channel-name') + "?")) {
      var channel_id = $(this).data('channel');
      var url = "/api/channels/" + channel_id + "/delete_channel/";
      $.ajax({
          url: url,
          method: "POST",
          success: function(data) {
            $("#item-" + channel_id).remove();
            update_channel_count();
          }, error: function(message) {
            alert(message.responseText);
          }
      });
    }

  })
});

function update_channel_count() {
  var matches = $(".channel-row:visible");
  $(".channel-count").text("Showing " + matches.length + " Channel" + ((matches.length === 1)? "..." : "s..."));
  $(".default-item").css('display', (matches.length)? 'none' : 'block');
}