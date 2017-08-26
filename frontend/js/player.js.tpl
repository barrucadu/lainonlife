const LainPlayer = (() => {
    const audioContext = new window.AudioContext();
    const audioTag = document.getElementById("audio");
    audioTag.volume = 0.51;
    let updateInterval;

    function changeSource(source) {
        const paused = audioTag.paused;
        // Use either the ogg or mp3 stream, depending on what the current one is.
        if(audioTag.currentSrc.endsWith("ogg")) {
            audioTag.src = "{{ icecast_stream_url_base }}/" + source + ".ogg";
        } else {
            audioTag.src = "{{ icecast_stream_url_base }}/" + source + ".mp3";
        }

        // Load the new audio stream.
        audioTag.load();

        // Start playing, if it was before.
        if(!paused) {
            audioTag.play();
        }
    }

    function updatePlayButton() {
        const button = document.getElementById("play-toggle");
        if(audioTag.paused) {
            button.classList.remove('fa-pause');
            button.classList.add('fa-play');
        } else {
            button.classList.remove('fa-play');
            button.classList.add('fa-pause');
        }
    }

    function togglePlay() {
        if(audioTag.paused) {
            audioTag.play();
        } else {
            audioTag.pause();
        }
        updatePlayButton();
    }

    function updateVolumeButton() {
        // Updates the volume button icon accoring to the volume
        volumebtn = document.getElementById("volume-button");
        if (audioTag.volume === 0) {
            volumebtn.classList.remove('fa-volume-up');
            volumebtn.classList.remove('fa-volume-down');
            volumebtn.classList.add('fa-volume-off');
        } else if (audioTag.volume > 0.51) {
            volumebtn.classList.remove('fa-volume-down');
            volumebtn.classList.remove('fa-volume-off');
            volumebtn.classList.add('fa-volume-up');
        } else {
            volumebtn.classList.remove('fa-volume-up');
            volumebtn.classList.remove('fa-volume-off');
            volumebtn.classList.add('fa-volume-down');
        }
    }

    function cycleVolume() {
        if (audioTag.volume < 0.51) {
            audioTag.volume = 0.51;
        } else if (audioTag.volume < 1) {
            audioTag.volume = 1;
        } else {
            audioTag.volume = 0;
        }
        updateVolumeButton();
    }

    function updateProgress(prgs) {
        // expects an object as the parameter that looks like this:
        //      {length: value, elapsed: value, live: boolean value}

        const bar       = document.getElementById('track-progress');
        const timeLabel = document.getElementById('time-label');

        function getCurrentTime(time) {
            let prefix = "";

            if (time < 0){
                time *= -1;
                prefix = "-";
            }
            const min = Math.floor(time / 60);
            let sec = Math.round(time - min * 60);

            if (sec < 10) {
                sec = "0" + sec;
            }

            return `${prefix}${min}:${sec}`;
        }

        function setProgressTo(elapsed) {
            let realElapsed = Math.min(elapsed, prgs.length);
            let progress    = Math.round(realElapsed/prgs.length*100);
            timeLabel.innerText = `${getCurrentTime(realElapsed)} / ${getCurrentTime(prgs.length)}`;
            bar.style.width = `${progress}%`;
        }

        function setLiveProgressTo(elapsed) {
            timeLabel.innerText = `${getCurrentTime(elapsed)} / ??:??`;
            bar.style.width = `0%`;
        }

        var progressFun = (prgs.live) ? setLiveProgressTo : setProgressTo;

        progressFun(prgs.elapsed);

        // smooth progressbar update
        clearInterval(updateInterval);
        let currentTimeInSeconds = prgs.elapsed;

        updateInterval = setInterval(() => {
            currentTimeInSeconds++;
            progressFun(currentTimeInSeconds);
        }, 1000);
    }

    return {
        togglePlay: () => togglePlay(),
        changeChannel: (channel) => changeSource(channel),
        cycleVolume: () => cycleVolume(),
        updateProgress: (progressObject) => updateProgress(progressObject),
    };
})();
