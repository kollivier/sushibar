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

      // POST
      var channel_control_url = "/api/channels/" + channel_id + "/control/";
      // post_data = {"command":"start", "options": JSON.stringify({"--publish": false}) }
      post_data = {
        "command": "start",
        "args": JSON.stringify({}),
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
    $(".channel-count").text("Showing " + matches.length + " Channel" + ((matches.length === 1)? "..." : "s..."))
  });
});
