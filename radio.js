// The initial channel
var channel = "everything";

function ajax_with_status_json(func) {
    let httpRequest = new XMLHttpRequest();
    httpRequest.onreadystatechange = function() {
        if(httpRequest.readyState === XMLHttpRequest.DONE && httpRequest.status === 200) {
            let response = JSON.parse(httpRequest.responseText);
            func(response);
        };
    };

    httpRequest.open("GET", "/radio/status-json.xsl");
    httpRequest.send();
}

function populate_channel_list() {
    ajax_with_status_json(function(response) {
        // Get the list of channels, excluding "everything".
        let channels = [];
        for(id in response.icestats.source) {
            let source = response.icestats.source[id];
            let sname = source.server_name.substr(0, source.server_name.length - 6);
            if(source.server_name.endsWith(" (ogg)") && sname != "everything") {
                channels.push(sname);
            }
        }

        // Sort them.
        channels.sort();

        // Add to the selector drop-down.
        let dropdown = document.getElementById("channel");
        for(id in channels) {
            let channel = channels[id];
            dropdown.options[dropdown.options.length] = new Option(channel, channel);
        }
    });
}

function check_status() {
    ajax_with_status_json(function(response) {
        let listeners = 0;
        let listenersPeak = 0;
        let artist = "";
        let title = "";
        let description = "";

        // Find the stats for the appropriate output.
        for(id in response.icestats.source) {
            let source = response.icestats.source[id];

            // Assume that the listeners of the ogg and mp3 streams
            // are disjoint and just add them.  Bigger numbers are
            // better, right?
            if(source.server_name.startsWith(channel + " (")) {
                listeners     += source.listeners;
                listenersPeak += source.listener_peak;
            }
            // For some reason the mp3 output has mangled unicode.
            // Probably something to do with how MPD is transcoding,
            // so only get the artist and title from the ogg stream.
            if(source.server_name == channel + " (ogg)") {
                artist = source.artist;
                title  = source.title;
                description = source.server_description;
            }
        }

        // Update the stats on the page.
        document.getElementById("nowplaying").innerText = artist + " - " + title;
        document.getElementById("listeners").innerText  = listeners + " (peak: " + listenersPeak + ")";

        // Update the channel description, in case it's changed.
        document.getElementById("description1").innerText = description;
        document.getElementById("description2").innerText = description;
    });
}

function change_channel(e) {
    let audio  = document.getElementById("audio");
    let paused = audio.paused;

    // Update the channel
    channel = e.value;

    // Use either the ogg or mp3 stream, depending on what the current one is.
    if(audio.currentSrc.endsWith("ogg")) {
        audio.src = "/radio/" + channel + ".ogg";
    } else {
        audio.src = "/radio/" + channel + ".mp3";
    }

    // Load the new audio stream.
    audio.load();

    // Start playing, if it was before.
    if(!paused) {
        audio.play();
    }

    // Update the stream links.
    document.getElementById("ogglink").href = "/radio/" + channel + ".ogg.m3u";
    document.getElementById("mp3link").href = "/radio/" + channel + ".mp3.m3u";

    // Update the file list link.
    document.getElementById("fileslink").href = "/file-list/" + channel + ".html";

    // Update the status.
    check_status();
}

// Show and hide things
let show = document.getElementsByClassName("withscript");
let hide = document.getElementsByClassName("noscript");
for(let i = 0; i < show.length; i++) { show[i].style.display = (show[i].tagName == "DIV") ? "block" : "inline"; }
for(let i = 0; i < hide.length; i++) { hide[i].style.display = "none"; }

// Populate the channel list.
populate_channel_list();

// Get the initial status and set a timer to regularly update it.
check_status();
setInterval(check_status, 15000);
