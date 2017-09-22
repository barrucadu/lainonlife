// The default channel
const DEFAULT_CHANNEL = "{{ default_channel }}";

// The initial channel
var channel = DEFAULT_CHANNEL;

// Recurring timers
let playlistPoll;
let statusPoll;
let schedulePoll;

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
    ajax_with_json("{{ icecast_status_url }}", function(response) {
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
    function format_track(track){
        return (track.artist) ? (track.artist + " - " + track.title) : track.title;
    }

    function add_track_to_tbody(tbody, track, acc, ago) {
        // Create row and cells
        let row   = tbody.insertRow(tbody.rows.length);
        let dcell = row.insertCell(0);
        let tcell = row.insertCell(ago ? 1 : 0);
        dcell.className = "dur";
        tcell.className = "track";

        // The track
        tcell.innerText = format_track(track);

        // The duration
        let time = "";
        if(acc < 60) {
            time = "under a min";
        } else {
            time = Math.round(acc / 60);
            time += " min" + ((time==1) ? "" : "s");
        }
        dcell.innerText = ago ? time + " ago" : "in " + time;

        // New accumulator
        return acc + parseFloat(track.time);
    }

    function swap_tbody(id, tbody) {
        let old = document.getElementById(id);
        old.parentNode.replaceChild(tbody, old);
        tbody.id = id;
    }

    ajax_with_json("/playlist/" + channel + ".json", function(response) {
        // Update the "last played"
        let new_lastplayed = document.createElement("tbody");
        let ago            = parseFloat(response.elapsed);
        for(let i in response.before) {
            ago = add_track_to_tbody(new_lastplayed, response.before[i], ago, true);
        }
        swap_tbody("lastplayed_body", new_lastplayed);

        // Update the "now playing"
        document.getElementById("nowplaying").innerText = format_track(response.current);
        document.getElementById("nowalbum").innerText = response.current.album;

        // check for livestream
        if (response.stream_data !== undefined && response.stream_data.live){
            let fake_queue = document.createElement("tbody");
            let fake_row = fake_queue.insertRow(0);

            let stream_desc_cell = fake_row.insertCell(0);
            stream_desc_cell.innerText = (response.stream_data.stream_desc || '');
            stream_desc_cell.style.width = "66%";
            stream_desc_cell.style.textAlign = "left";

            let dj_pic_cell = fake_row.insertCell(1);
            dj_pic_cell.style.width = "33%";

            let dj_pic_img = document.createElement("img");
            dj_pic_img.id = 'dj_pic';
            dj_pic_img.src = (response.stream_data.dj_pic || '');
            dj_pic_cell.appendChild(dj_pic_img);

            let dj_name = document.createElement("span");
            dj_name.innerText = 'Current DJ: ' + response.stream_data.dj_name;
            dj_pic_cell.appendChild(dj_name);

            swap_tbody("queue_body", fake_queue);
        } else {
            let new_queue = document.createElement("tbody");
            let until     = parseFloat(response.current.time) - parseFloat(response.elapsed);
            for(let i in response.after) {
                until = add_track_to_tbody(new_queue, response.after[i], until, false);
            }
            swap_tbody("queue_body", new_queue);
        }

        LainPlayer.updateProgress({
            length: response.current.time,
            elapsed: response.elapsed,
            live: response.stream_data.live
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
    document.getElementById("ogglink").href = "{{ icecast_stream_url_base }}/" + channel + ".ogg.m3u";
    document.getElementById("mp3link").href = "{{ icecast_stream_url_base }}/" + channel + ".mp3.m3u";

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

function populate_schedule() {
    ajax_with_json("/schedule.json", function(response) {
        for(let i = 0; i < 7; i++) {
            document.getElementById('sched_' + i).innerText = 'None';
        }

        for(let i = 0; i < response.length; i++) {
            if(response[i].length > 0) {
                document.getElementById('sched_' + i).innerText = response[i];
            }
        }
    });
}

window.onload = () => {
    // Show and hide things
    let show = document.getElementsByClassName("withscript");
    let hide = document.getElementsByClassName("noscript");
    for(let i = 0; i < show.length; i++) {
        if(show[i].tagName == "DIV" || show[i].tagName == "HEADER" || show[i].tagName == "TABLE") {
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

    // refresh the schedule every 30 minutes
    populate_schedule();
    schedulePoll = setInterval(populate_schedule, 1800000);
};
