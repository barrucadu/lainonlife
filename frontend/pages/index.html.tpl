{% extends "wrapper.tpl" %}

{% block head %}
<script type="text/javascript">
const ICECAST_STREAM_URL_BASE = "{{ icecast_stream_url_base }}";
const DEFAULT_CHANNEL = "{{ default_channel }}"; 
const ICECAST_STATUS_URL = "{{ icecast_status_url }}"; 
</script>
<script defer src="/js/player.js" type="text/javascript"></script>
<script defer src="/js/radio.js"  type="text/javascript"></script>
{% endblock %}

{% block body %}
<div class="box">
  <div class="controls">
    <div class="lainplayer" id="lainplayer">
      <div class="lainplayer-row">
        <div class="withscript current-track">
          <header>
            <h1 id="nowplaying"></h1>
            <h2 id="nowalbum"></h2>
          </header>
        </div>
        <div class="button-group playback-buttons">
          <div class="button-section">
              <div class="withscript button inline" onclick="LainPlayer.stop()">
                <i id="stop-button" class="fa fa-stop" aria-hidden="true"></i>
              </div>

              <div class="withscript button inline" onclick="LainPlayer.togglePlay()">
                <i id="play-toggle" class="fa fa-play" aria-hidden="true"></i>
              </div>
          </div>
          <div class="withscript button inline" onclick="LainPlayer.cycleVolume()">
            <i id="volume-button" class="fa fa-volume-down" aria-hidden="true"></i>
          </div>
        </div>
      </div>
      <div class="lainplayer-row progress">
        <div class="inner-player">
          <audio controls preload="none" id="audio" class="noscript">
            <source src="{{ icecast_stream_url_base }}/{{ default_channel }}.ogg" type="audio/ogg"/>
            <source src="{{ icecast_stream_url_base }}/{{ default_channel }}.mp3" type="audio/mpeg"/>
            <em>Your browser lacks support for OGG Vorbis files. Please open the M3U file or XSPF file in a multimedia player.</em>
          </audio>
          <div class="progressbar withscript inline">
            <div id="track-progress"></div>
          </div>
        </div>
        <div class="withscript progress-label">
          <span id="time-label"></span>
        </div>
      </div>
    </div>
    
    <div class="channel-row">
      <div class="channel-row-block">
        [ <span class="inlineheading">channel:</span>
          <span class="noscript">{{ default_channel }}</span>
          <select class="withscript" id="channel" onchange="change_channel(this)"></select>
        ]
      </div>
      <div class="channel-row-block">
        [ <span class="inlineheading">link:</span>   
          <a id="mp3link" href="{{ icecast_stream_url_base }}/{{ default_channel }}.mp3">mp3</a> 
        ]
      </div>
      <div class="channel-row-block">
        [ <span class="inlineheading">files:</span> <a id="fileslink" href="/file-list/{{ default_channel }}.html">list</a> ]
      </div>
      <div class="channel-row-block">
        <span class="withscript">[ <span class="inlineheading">listeners:</span> <span id="listeners"></span> ]</span>
      </div>
    </div>
  </div>

  <hr/>

  <div class="withscript">
    <table id="playlist" class="playlist">
      <tbody id="playlist_body"></tbody>
    </table>
  </div>

  <div class="alert noscript">
    <p>Enable Javascript for the channel features to work.</p>

    <p class="plain">Or don't, I'm not your mom.</p>
  </div>
</div>

<footer>
  [
  <a href="/graphs/dashboard/db/lainon-life">graphs</a>
  /
  <a href="https://github.com/barrucadu/lainonlife">git</a>
  /
  <a href="https://social.lainon.life">pleroma</a>
  /
  <a href="/donate.html">donate</a>
  ]
</footer>
{% endblock %}
