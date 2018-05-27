var new_group_id = "";
var replay_group_id = "";
var all_images = {};

$(function() {
  $("#launch-link").on("show.bs.tab", function() {
    loadImages();
  });

  $("#new-link").on("show.bs.tab", function() {

  });

  function loadImages() {
    $.getJSON("/archive/list/images", function(data) {
      $("#run-image-select").empty();
      all_images = {}
      $.each(data.images, function(i, value) {
        all_images[value.name] = value;
        $('#run-image-select').append('<option value=' + value.name + '>' + value.name + '</option>');
      });
    });
  }

  $.each(image_list, function(i, value) {
    all_images[value.name] = value;
  });

  function init_launch_image_ui() {
    var name = $("#run-image-select").val();

    $("#image_download").attr("href", "/archive/download/" + name);
    $("#image_download").text(name + ".tar.gz");

    $("#image_start_url").text(all_images[name].url);
    $("#image_size").text(bytesToSize(all_images[name].size));
  }

  init_launch_image_ui();

  $("#run-image-select").change(function() {
    init_launch_image_ui();
  });


  $("#new-url").change(function() {
    var parts = $("#new-url").val().split("/");
    $("#image-name").val(parts[parts.length - 1]);
  });


  $("#new-archive").submit(function(event) {
    event.preventDefault();

    var proto = (window.location.protocol == "https:" ? "wss://" : "ws://");

    var ws_url = proto + window.location.host + "/archive/ws/new";
    ws_url += "?" + $.param({"url": $("#new-url").val(),
                             "email": $("#email").val(),
                             "password": $("#password").val(),
                             "image-name": $("#image-name").val(),
                             "auth-code": $("#auth-code").val()
                            })
    console.log(ws_url);

    var ws = new WebSocket(ws_url);

    ws.onmessage = function(event) {
      var data = JSON.parse(event.data);

      console.log(data);

      if (data.msg) {
        $("#status-new").text(data.msg);
      }

      if (data.error) {
        $("#status-new").addClass("error-msg");
        return;
      } else {
        $("#status-new").removeClass("error-msg");
      }

      if (data.launch_id) {
        new_group_id  = data.launch_id;

        //$("#commit button").attr("disabled", false);
        $("#cancel-new").attr("disabled", false);
      }

      if (data.import_reqid) {
        console.log("inited: " + data.import_reqid);
        init_browser(data.import_reqid, "#import-browser");
      }

      if (data.auto_reqids) {
        for (var i in data.auto_reqids) {
          init_browser(data.auto_reqids[i], "#auto-" + i);
        }
      }

      if (data.done) {
        $("#cancel-new").attr("disabled", true);
      }
    };

    return true;
  });


  $("#commit").submit(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/commit/" + replay_group_id,
            "data": {"name": $("#run-image-name").val()},
            "dataType": "json"}).done(function(data) {

      console.log(data);
    });

    return true;
  });


  $("#cancel-new").click(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/delete/" + new_group_id,
            "dataType": "json"}).done(function(data) {

      console.log(data);

      $("#status-new").text("Preservation Canceled");
      $("#import-browser")[0].src = "about:blank";

      for (var i = 0; i < 4; i++) {
        $("#auto-" + i)[0].src = "about:blank";
      }
    });

    return true;
  });


  $("#launch").submit(function(event) {
    $("#launch_div").hide();

    if (replay_group_id) {
      cancel_replay();
    }

    $("#launch").attr("disabled", true);

    event.preventDefault();

    var proto = (window.location.protocol == "https:" ? "wss://" : "ws://");

    var ws_url = proto + window.location.host + "/archive/ws/launch/" + $("#run-image-select").val();

    console.log(ws_url);

    var ws = new WebSocket(ws_url);

    ws.onmessage = function(event) {
      var data = JSON.parse(event.data);

      console.log(data);

      if (data.msg) {
        $("#status-launch").text(data.msg);
      }

      if (data.error) {
        $("#status-launch").addClass("error-msg");
        return;
      } else {
        $("#status-launch").removeClass("error-msg");
      }

      if (data.launch_id) {
        replay_group_id = data.launch_id;

        $("#cancel-launch").attr("disabled", false);
      }

      if (data.launch_url) {
        $("#launch_div").show();
        $("#launch_url").attr("href", data.launch_url);
      }

      if (data.reqid) {
        init_browser(data.reqid, "#browser");
      }

    };

  });

  $("#cancel-launch").click(cancel_replay);

  function cancel_replay(event) {
    if (event) {
      event.preventDefault();
    }

    $.ajax({"url": "/archive/delete/" + replay_group_id,
            "dataType": "json"}).done(function(data) {

      console.log(data);

      $("#status-launch").text("Image Stopped");
      $("#browser")[0].src = "about:blank";
      $("#launch_div").hide();

      $("#cancel-launch").attr("disabled", true);
    });

    replay_group_id = undefined;
    $("#launch").attr("disabled", false);

    return true;
  };

});


function init_browser(reqid, dom_id) {
  $(dom_id)[0].src = window.location.protocol + "//" + window.location.host + "/attach/" + reqid;
}

function bytesToSize(bytes) {
    var sizes = ['bytes', 'KB', 'MB', 'GB', 'TB'];
    if (bytes == 0) return 'n/a';
    var i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
    if (i == 0) return bytes + ' ' + sizes[i];
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i];
};
