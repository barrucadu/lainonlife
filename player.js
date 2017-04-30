const LainPlayer = (() => {
    const playerHTML = "<a id='play-toggle' onclick='LainPlayer.play()'><i class='fa fa-play' aria-hidden='true'></i></a><i id=volume-button class='fa fa-volume-up' aria-hidden='true' onclick='LainPlayer.toggleMute()'></i><input type='range' value=0.51 min=0 max=1  step=0.01 oninput='LainPlayer.changeVolume(this.value)'/>"
    const audioContext = new window.AudioContext();
    const audioTag = document.getElementById("audio");
    let muted = false;
    let volume = 0.51;
    audioTag.volume =  volume;

    function replacePlayer() {
        const oldPlayer = audioTag;
        const newPlayer = document.createElement("div")
        newPlayer.setAttribute("id", "lainplayer");
        newPlayer.innerHTML = playerHTML;
        // hide old player and add the new one
        oldPlayer.setAttribute("style", "display:none;");
        oldPlayer.after(newPlayer);

    }

    function cangeSource(source) {
        console.log("fug");
        const paused = audioTag.paused;
        console.log(paused)
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
            button.innerHTML = '<i class="fa fa-play" aria-hidden="true"></i>';
            button.setAttribute("onclick", "LainPlayer.play()");
        } else {
            button.innerHTML = '<i class="fa fa-pause" aria-hidden="true"></i>';
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
            document.getElementById("lainplayer").children[2].value = 0;
            muted = true;
            updateVolumeButton();
        } else {
            audioTag.volume = volume;
            document.getElementById("lainplayer").children[2].value = volume;
            muted = false;
            updateVolumeButton();
        }
    }

    return {
        init: () => replacePlayer(),
        play: () => { audioTag.play(); updatePlayButton(); },
        pause: () => { audioTag.pause(); updatePlayButton(); },
        changeChannel: (channel) => cangeSource(channel),
        changeVolume: (value) => {
            audioTag.volume = value;
            volume = value;
            muted = !(value > 0);
            updateVolumeButton();
        },
        toggleMute: () => toggleMute(),
    }
})();
