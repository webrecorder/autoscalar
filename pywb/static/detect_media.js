
(function() {
  __wr_media_done = false;

  document.addEventListener("readystatechange", init);

  function init() {
    if (document.readyState != "complete") { return; }

    var rules = [
      {rx: /w\.soundcloud\.com/,
       suffix: "&auto_play=true",
      },

      {rx: /player\.vimeo\.com/,
       suffix: "&autoplay=1"},

      {rx: /youtube\.com\/embed\//,
       suffix: "&autoplay=1"},
    ];

    var appendSuffix = null;
    var is_autoplay = false;

    for (var i in rules) {
      if (window.location.href.search(rules[i].rx) >= 0) {
        is_autoplay = true;
        if (!window.location.search.endsWith(rules[i].suffix)) {
          appendSuffix = rules[i].suffix;
        }
        break;
      }
    }

    if (appendSuffix) {
      setTimeout(function() { window.location.href += appendSuffix; }, 2000);
      return;
    }

    find_video_audio();
  }

  function find_video_audio() {
    function detect_play(elem) {
      elem.addEventListener("playing", function() {
        console.log("playing!");
        __wr_media_done = true;
      });

      if (elem.paused) {
        elem.play();
      }
    }
    document.querySelectorAll("video").forEach(detect_play);
    document.querySelectorAll("audio").forEach(detect_play);

    if (!__wr_media_done) {
      setTimeout(find_video_audio, 3000);
    }
  }

})();

