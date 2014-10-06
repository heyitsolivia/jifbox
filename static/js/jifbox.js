(function() {

  var streaming = false,
      video        = document.querySelector('#vdo'),
      canvas       = document.querySelector('#cnvs'),
      photo        = document.querySelector('#photo'),
      startbutton  = document.querySelector('button#snap'),
      width = 320,
      height = 0,
      count = -1;

  navigator.getMedia = ( navigator.getUserMedia ||
                         navigator.webkitGetUserMedia ||
                         navigator.mozGetUserMedia ||
                         navigator.msGetUserMedia);

  navigator.getMedia(
    {
      video: true,
      audio: false
    },
    function(stream) {
      if (navigator.mozGetUserMedia) {
        video.mozSrcObject = stream;
      } else {
        var vendorURL = window.URL || window.webkitURL;
        video.src = vendorURL.createObjectURL(stream);
      }
      video.play();
    },
    function(err) {
      console.log("An error occured! " + err);
    }
  );

  video.addEventListener('canplay', function(ev){
    if (!streaming) {
      height = video.videoHeight / (video.videoWidth/width);
      video.setAttribute('width', width);
      video.setAttribute('height', height);
      canvas.setAttribute('width', width);
      canvas.setAttribute('height', height);
      streaming = true;
    }
  }, false);

  function takepicture() {
    canvas.width = width;
    canvas.height = height;
    canvas.getContext('2d').drawImage(video, 0, 0, width, height);
    var data = canvas.toDataURL('image/png');

    count++;
    if (count === 12) {
      gifit();
    }
    count = count % 12;

    document.querySelector('.photo' + count).setAttribute('src', data);
  }

  function gifit() {

    var encoder = new GIFEncoder();
    encoder.setRepeat(0);
    encoder.setDelay(150);
    encoder.start();

    var context = canvas.getContext('2d');

    for (var i = 0; i < 12; i++) {
      console.log(i);
      var img = document.querySelector('.photo' + i);
      context.drawImage(img, 0, 0, width, height);
      encoder.addFrame(context);
    }

    encoder.finish();

    var bin = encoder.stream().getData();
    var url = 'data:image/gif;base64,' + encode64(bin);
    document.querySelector('#jif').src = url;
  }

  startbutton.addEventListener('click', function(ev){
    takepicture();
    ev.preventDefault();
  }, false);

})();
