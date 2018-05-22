var group_id = "";


$(function() {
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
                             "image-name": $("#image-name").val()
                            })
    console.log(ws_url);

    var ws = new WebSocket(ws_url);

    ws.onmessage = function(event) {
      var data = JSON.parse(event.data);

      console.log(data);

      if (data.msg) {
        $("#status").text(data.msg);
      }

      if (data.error) {
        return;
      }

      if (data.launch_id) {
        group_id = data.launch_id;

        $("#commit button").attr("disabled", false);
        $("#cancel").attr("disabled", false);
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
    };

    return true;
  });


  $("#commit").submit(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/commit/" + group_id,
            "data": {"name": $("#run-image-name").val()},
            "dataType": "json"}).done(function(data) {

      console.log(data);
    });

    return true;
  });

  $("#cancel").click(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/delete/" + group_id,
            "dataType": "json"}).done(function(data) {

      console.log(data);
    });

    return true;
  });


  $("#launch").submit(function(event) {
    event.preventDefault();

    var proto = (window.location.protocol == "https:" ? "wss://" : "ws://");

    var ws_url = proto + window.location.host + "/archive/ws/launch/" + $("#run-image-name").val();

    console.log(ws_url);

    var ws = new WebSocket(ws_url);

    ws.onmessage = function(event) {
      var data = JSON.parse(event.data);

      console.log(data);

      if (data.msg) {
        $("#status").text(data.msg);
      }

      if (data.error) {
        return;
      }

      if (data.launch_id) {
        group_id = data.launch_id;
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

});


function init_browser(reqid, dom_id) {
  $(dom_id)[0].src = window.location.protocol + "//" + window.location.host + "/attach/" + reqid;
}
