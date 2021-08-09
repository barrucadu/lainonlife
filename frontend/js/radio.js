// The initial channel
let channel = DEFAULT_CHANNEL;

// Recurring timers
let playlistPoll;
let statusPoll;

function ajax_with_json(url, func) {
    let httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function() {
        if(httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
            let response = JSON.parse(httpRequest.responseText);
            func(response);
        }
    };

    httpRequest.open("GET", url);
    httpRequest.send();
}

function populate_channel_list() {
    ajax_with_json(ICECAST_STATUS_URL, function(response) {
        // Get the list of channels, the default.
        let channels = [];
        for(let id in response.icestats.source) {
            let source = response.icestats.source[id];
            let sname = source.server_name;
            if(sname !== undefined && sname.startsWith("[mpd] ") && sname.endsWith(" (ogg)")) {
                channels.push(sname.substr(6, sname.length-12));
            }
        }

        // Sort them.
        channels.sort();

        // Add to the selector drop-down.
        let dropdown = document.getElementById("channel");
        for(let id in channels) {
            let channel = channels[id];
            dropdown.options[dropdown.options.length] = new Option(channel, channel, channel == DEFAULT_CHANNEL, channel == DEFAULT_CHANNEL);
        }
    });
}

function check_playlist() {
    function format_track(track) {
        return (track.artist) ? (track.artist + " - " + track.title) : track.title;
    }

    function set_media_session(track) {
        if ('mediaSession' in navigator) {
            navigator.mediaSession.metadata = new MediaMetadata({
                title: track.title,
                artist: track.artist,
                album: track.album,
            });
        }	
    }

    function add_track_to_tbody(tbody, track, acc, ago) {
        // Create row and cells
        let row   = tbody.insertRow((ago === true) ? 0 : tbody.rows.length);
        let dcell = row.insertCell(0);
        let tcell = row.insertCell(0);
        dcell.className = "dur";
        tcell.className = "track";

        // The track
        tcell.innerText = format_track(track);

        if(acc == undefined) {
            dcell.classList.add("current_track");
            tcell.classList.add("current_track");

            let arrow = document.createElement("i");
            arrow.classList.add("fa");
            arrow.classList.add("fa-arrow-circle-o-left");
            dcell.appendChild(arrow);
        } else {
            // The duration
            let time = "";
            if(acc < 60) {
                time = "under a min";
            } else {
                time = Math.round(acc / 60);
                time += " min" + ((time==1) ? "" : "s");
            }
            dcell.innerText = ago ? time + " ago" : "in " + time;
        }

        // New accumulator
        return acc + parseFloat(track.time);
    }

    function swap_tbody(id, tbody) {
        let old = document.getElementById(id);
        old.parentNode.replaceChild(tbody, old);
        tbody.id = id;
    }

    ajax_with_json(`/playlist/${channel}.json`, function(response) {
        // Update the "now playing"
        document.getElementById("nowplaying").innerText = format_track(response.current);
        document.getElementById("nowalbum").innerText = response.current.album;
        set_media_session(response.current);

        let new_playlist = document.createElement("tbody");
        let until = parseFloat(response.current.time) - parseFloat(response.elapsed);
        let ago   = parseFloat(response.elapsed);
        for(let i in response.before) {
            ago = add_track_to_tbody(new_playlist, response.before[i], ago, true);
        }
        add_track_to_tbody(new_playlist, response.current, undefined, false);
        for(let i in response.after) {
            until = add_track_to_tbody(new_playlist, response.after[i], until, false);
        }
        swap_tbody("playlist_body", new_playlist);

        LainPlayer.updateProgress({
            length: response.current.time,
            elapsed: response.elapsed,
        });

        // Update the current/peak listeners counts
        document.getElementById("listeners").innerText = `${response.listeners.current}`;
        if ('peak' in response.listeners) {
            document.getElementById("listeners").innerText += ` (peak ${response.listeners.peak})`;
        }
    });
}

function change_channel(e) {
    channel = e.value;
    LainPlayer.changeChannel(channel);

    // Update the stream links.
    document.getElementById("ogglink").href = `${ICECAST_STREAM_URL_BASE}/${channel}.ogg.m3u`;
    document.getElementById("mp3link").href = `${ICECAST_STREAM_URL_BASE}/${channel}.mp3.m3u`;

    // Update the file list link.
    document.getElementById("fileslink").href = "/file-list/" + channel + ".html";

    // clear the running Intervals
    // this is needed for the smooth progressbar update to be in sync
    clearInterval(statusPoll);
    clearInterval(playlistPoll);

    // Update the playlist and reset the Intervals
    check_playlist();
    playlistPoll = setInterval(check_playlist, 15000);
}

window.onload = () => {
    // Show and hide things
    let show = document.getElementsByClassName("withscript");
    let hide = document.getElementsByClassName("noscript");
    for(let i = 0; i < show.length; i++) {
        if (show[i].classList.contains("inline")) {
            show[i].style.display = "inline-block";
        } else if(show[i].tagName == "DIV" || show[i].tagName == "HEADER" || show[i].tagName == "TABLE") {
            show[i].style.display = "block";
        } else if(show[i].tagName == "TD") {
            show[i].style.display = "table-cell";
        } else {
            show[i].style.display = "inline";
        }
    }
    for(let i = 0; i < hide.length; i++) { hide[i].style.display = "none"; }

    // Populate the channel list.
    populate_channel_list();

    // Get the initial playlist and set a timer to regularly update it.
    check_playlist();
    playlistPoll = setInterval(check_playlist, 15000);

    document.addEventListener('keyup', (e) => {
        if(e.keyCode == 32){
            LainPlayer.togglePlay()
        }
    });
};
