(function() {
  document.addEventListener("readystatechange", function() {
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

    for (var i in rules) {
      if (window.location.href.search(rules[i].rx) >= 0) {
        //if (window.location.href.split(rules[i].suffix).length <= min) {
        if (!window.location.search.endsWith(rules[i].suffix)) {
          appendSuffix = rules[i].suffix;
        }
        break;
      }
    }

    if (appendSuffix) {
      setTimeout(function() { window.location.href += appendSuffix; }, 2000);
    }

    var videos = document.querySelectorAll("video");

    for (var v in videos) {
      videos[v].play();
    }

    var audios = document.querySelectorAll("audio");

    for (var a in audios) {
      audios[a].play();
    }

  });

})();

