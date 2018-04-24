$(function() {
  $("#new-archive").submit(function(event) {
    event.preventDefault();

    $.ajax({"url": "/archive/new/" + $("#new-url").val(),
            "dataType": "json"}).done(function(data, status, xhr) {

      console.log(data);

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
});


function init_browser(reqid, dom_id) {
  $(dom_id)[0].src = "http://localhost:9020/attach/" + reqid;
}
