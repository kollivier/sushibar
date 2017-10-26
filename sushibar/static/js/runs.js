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


$(function() {
  $('.stage-progress').tooltip();

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
  $('.content-tree > .topic').click(function() {
    var el = $(this);
    if(!el.data('loaded')) {
      var load_tre_url = "/api/channels/" + channel_id + "/load_node_tree/";
      $.post(load_tre_url, {"node_id": el.data('node-id')}, function() {
        el.find('ul').slideToggle(100);
        el.data('loaded', true);
      });
    } else {
      el.find('ul').slideToggle(100);
    }
  });


  var hash = window.location.hash;
  hash && $('.nav-link[href="' + hash + '"]').tab('show');

  $('.nav-link').click(function(e) {
    var new_hash = this['href'].substring(this['href'].indexOf('#')+1);
    history.replaceState(undefined, undefined, "#" + new_hash);
  });
});
