$(function() {
  $("#new-archive").submit(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/new/" + $("#new-url").val(),
            "dataType": "json"}).done(function(data, status, xhr) {

      console.log(data);

      $("#group-id").val(data.id);

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


  $("#commit").click(function() {
    $.ajax({"url": "/archive/commit/" + $("#group-id").val(),
            "data": {"name": $("#image-name").val()},
            "dataType": "json"}).done(function(data) {

      console.log(data);
    });
    return true;
  });


  $("#launch").click(function() {
    $.ajax({"url": "/archive/launch/" + $("#image-name").val(),
            "data": {"url": $("#new-url").val()},
            "dataType": "json"}).done(function(data) {

      console.log(data);

      if (data.reqid) {
        init_browser(data.reqid, "#import-browser");
      }
    });
    return true;
  });





});


function init_browser(reqid, dom_id) {
  $(dom_id)[0].src = "http://localhost:9020/attach/" + reqid;
}
