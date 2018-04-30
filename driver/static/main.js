var group_id = "";


$(function() {
  $("#new-archive").submit(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/new/" + $("#new-url").val(),
            "dataType": "json"}).done(function(data, status, xhr) {

      console.log(data);

      group_id = data.id;

      $("#commit button").attr("disabled", false);
      $("#cancel").attr("disabled", false);

      if (data.reqid) {
        console.log("inited: " + data.reqid);
        init_browser(data.reqid, "#import-browser");
      }

      if (data.autos) {
        init_browser(data.autos[0], "#auto-1");
//        init_browser(data.autos[1], "#auto-2");
      }
    });

    return true;
  });


  $("#commit").submit(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/commit/" + group_id,
            "data": {"name": $("#image-name").val()},
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

    $.ajax({"url": "/archive/launch/" + $("#image-name").val(),
            "dataType": "json"}).done(function(data) {

      console.log(data);

      if (data.reqid) {
        init_browser(data.reqid, "#browser");
      }
    });
    return true;
  });

});


function init_browser(reqid, dom_id) {
  $(dom_id)[0].src = "http://localhost:9020/attach/" + reqid;
}
