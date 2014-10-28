(function() {

  // variable declaration 
  var streaming = false,
      video        = document.querySelector('#vdo'),
      canvas       = document.querySelector('#cnvs'),
      photo        = document.querySelector('#photo'),
      startbutton  = document.querySelector('button#snap'),
      burst_switch = document.querySelector('#burst-switch'),
      burst        = false,
      frames       = 12,
      frame_delay  = 250,
      snap_delay   = 500,
      width = 320,
      height = 0,
      count = -1,

      // instantiates a new gif object
      gif = new GIF({
        workers: 2,
        quality: 10,
        width: 320,
        height: 240,
        workerScript: '/static/gif.js/dist/gif.worker.js'
      });


  // Access to browser camera
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


  // Takes picture, draws image from canvas, sets img src attribute
  // adds img to gif frame
  // (could benefit from getting refactored into multiple single responsibility functions)
  function takepicture(){
    canvas.width = width;
    canvas.height = height;
    canvas.getContext('2d').drawImage(video, 0, 0, width, height);
    var data = canvas.toDataURL('image/png');
    

    count++;
    if ( count === frames ) {
      document.querySelector('#jif').src = '/static/gif.js/site/contents/images/loading.gif'
      gif.render();
    } else if ( burst ) {
      snapPhoto();
    }

    count = count % frames;

    document.querySelector('.photo' + count).setAttribute('src', data);
    gif.addFrame(document.querySelector('.photo' + count), {delay: frame_delay});
  }

  // Timer to call takepicture() when app is in burst mode
  function snapPhoto(){
    if (count < frames){
      setTimeout(takepicture, snap_delay);
    }
  }

  // gif event listener to generate url blob
  gif.on('finished', function(blob) {
    uploadGIF(blob);
    document.querySelector('#jif').src = URL.createObjectURL(blob);
    count = -1;
    gif.frames = [];
    gif.running = false;
  });

  // listens to checkbox for burst mode
  burst_switch.addEventListener('change', function(){
    burst = this.checked;
  });

  // event listener for the startbutton to take a picture
  startbutton.addEventListener('click', function(ev){
    prepCapture();
    ev.preventDefault();
  }, false);

  // Handles keyboard trigger
  document.addEventListener('keypress', function(ev){
    if ( ev.keyCode == 32 ){
      // spacebar to trigger capture
      prepCapture();
    } else if ( ev.keyCode == 122 ){
      // "z" key to check burst_switch
      burst_switch.checked = true;
      burst = true;
    } else if ( ev.keyCode == 120 ) {
      // "x" key to uncheck burst_switch
      burst_switch.checked = false;
      burst = false;
    }
  })

  function prepCapture(){
     burst == true ? snapPhoto() : takepicture();
  }

  // creates the img frames
  function createFrameEls(){
    for (var i = 0; i < frames; i++){
      var img = document.createElement('img');
      img.setAttribute('src', 'http://placekitten.com/g/320/240');
      img.setAttribute('class', 'photo' + i );
      img.setAttribute('alt', 'photo');
      document.querySelector('.snaps').appendChild(img);
    }
  }

  function applySettings(){
    var request = new XMLHttpRequest();
    request.open('GET', '/get-settings', true);
    request.send();
    request.onload = function() {
      if (request.status >= 200 && request.status < 400){
        // Success!
        data = JSON.parse(request.responseText);
        frames = data.frames;
        frame_delay = data.frame_delay;
        snap_delay = data.snap_delay;
      } else {
        console.log("hmm something isn't right")
      }
      createFrameEls();
    }
  }

  function uploadGIF(blob){

    var formData = new FormData();
    formData.append('giffile', blob, 'jif.gif');

    var request = new XMLHttpRequest();
    request.open('POST', '/giffed', true);
    request.send(formData);
    request.onload = function() {
      if (xhr.status === 200) {
        // done
      } else {
        // an error occured
      }
    }

  }

  applySettings();

})();