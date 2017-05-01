const LainPlayer = (() => {
    const audioContext = new window.AudioContext();
    const audioTag = document.getElementById("audio");
    let muted = false;
    let volume = 0.51;
    audioTag.volume =  volume;

    function changeSource(source) {
        const paused = audioTag.paused;
        // Use either the ogg or mp3 stream, depending on what the current one is.
        if(audioTag.currentSrc.endsWith("ogg")) {
            audioTag.src = "/radio/" + source + ".ogg";
        } else {
            audioTag.src = "/radio/" + source + ".mp3";
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
            button.setAttribute("onclick", "LainPlayer.play()");
        } else {
            button.classList.remove('fa-play');
            button.classList.add('fa-pause');
            button.setAttribute("onclick", "LainPlayer.pause()");
        }
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

    function toggleMute() {
        if (!muted) {
            audioTag.volume = 0;
            document.getElementById("volume-slider").value = 0;
            muted = true;
            updateVolumeButton();
        } else {
            audioTag.volume = volume;
            document.getElementById("volume-slider").value = volume;
            muted = false;
            updateVolumeButton();
        }
    }

    function updateProgress(prgs) {
        // expects an object as the parameter that looks like this:
        //      {length: value, elapsed: value}

        function getCurrentTime(time) {
             const min = Math.floor(time / 60);
             let sec = Math.round(time - min * 60);

             if (sec < 10) {
                 sec = "0" + sec;
             }

             return `${min}:${sec}`;
        }

        const bar  = document.getElementById('track-progress');
        const timeLabel = document.getElementById('time-label');
        const progress = Math.round(prgs.elapsed/prgs.length*100);
        timeLabel.innerText = getCurrentTime(prgs.elapsed);
        bar.value = progress;
        bar.innerText = `${progress}%`;
    }

    return {
        play: () => { audioTag.play(); updatePlayButton(); },
        pause: () => { audioTag.pause(); updatePlayButton(); },
        changeChannel: (channel) => changeSource(channel),
        changeVolume: (value) => {
            audioTag.volume = value;
            volume = value;
            muted = !(value > 0);
            updateVolumeButton();
        },
        toggleMute: () => toggleMute(),
        updateProgress: (progressObject) => updateProgress(progressObject),
    }
})();
