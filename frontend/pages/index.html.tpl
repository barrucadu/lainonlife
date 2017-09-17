{% extends "wrapper.tpl" %}

{% block head %}
<script defer src="/js/player.js" type="text/javascript"></script>
<script defer src="/js/radio.js"  type="text/javascript"></script>
{% endblock %}

{% block body %}
<div class="box">
  <div class="controls">
    <!-- Table for layout because I am not very good with CSS. Feel free to fix. -->
    <table id="lainplayer">
      <tr>
        <td class="withscript">
          <header>
            <h1 id="nowplaying"></h1>
            <h2 id="nowalbum"></h2>
          </header>
        </td>
        <td class="withscript button" style="text-align:right;" onclick="LainPlayer.togglePlay()">
          <i id="play-toggle" class="fa fa-play" aria-hidden="true"></i>
        </td>
        <td class="withscript button" style="text-align:left;" onclick="LainPlayer.cycleVolume()">
          <i id="volume-button" class="fa fa-volume-down" aria-hidden="true"></i>
        </td>
      </tr>
      <tr>
        <td>
          <audio controls preload="none" id="audio" class="noscript">
            <source src="{{ icecast_stream_url_base }}/{{ default_channel }}.ogg" type="audio/ogg"/>
            <source src="{{ icecast_stream_url_base }}/{{ default_channel }}.mp3" type="audio/mpeg"/>
            <em>Your browser lacks support for OGG Vorbis files. Please open the M3U file or XSPF file in a multimedia player.</em>
          </audio>
          <div class="progressbar withscript">
            <div id="track-progress"></div>
          </div>
        </td>
        <td colspan="2" class="withscript">
          <p id="time-label"><p>
        </td>
      </tr>
    </table>

    [ <span class="inlineheading">channel:</span>
      <span class="noscript">{{ default_channel }}</span>
      <select class="withscript" id="channel" onchange="change_channel(this)"></select>
    ]

    [ <span class="inlineheading">m3u:</span>   <a id="ogglink" href="{{ icecast_stream_url_base }}/{{ default_channel }}.ogg.m3u">ogg</a> / <a id="mp3link" href="{{ icecast_stream_url_base }}/{{ default_channel }}.mp3.m3u">mp3</a> ]
    [ <span class="inlineheading">files:</span> <a id="fileslink" href="/file-list/{{ default_channel }}.html">list</a> ]
  </div>

  <hr/>

  <div class="withscript playbox">
    <div class="flex">
      <header class="col left">Last Played</header>
      <header class="col right" id="queue_header">Queue</header>
      <div class="col left" id="lastplayed">
        <table>
          <tbody id="lastplayed_body"></tbody>
        </table>
      </div>
      <div class="col right" id="queue">
        <table>
          <tbody id="queue_body"></tbody>
        </table>
      </div>
    </div>
    <footer id="listeners"></footer>
  </div>

  <div class="alert noscript">
    <p>Enable Javascript for the channel features to work.</p>

    <p class="plain">Or don't, I'm not your mom.</p>
  </div>

  <hr/>

  <p>Want to be a radio star?  <a href="/bump.html">Submit a bump today!</a></p>
  <p>Think the radio is missing something?  <a href="/request.html">Submit a request!</a></p>
</div>

<div id="schedule" class="overlay">
  <a class="cancel_popup" href="#"></a>
  <div class="popup">
    <div class="content" id="schedule_div">
      <h1>Scheduled Events</h1>

      <table class="withscript">
        <tbody>
          <tr><td>Monday</td><td id="sched_0"></td></tr>
          <tr><td>Tuesday</td><td id="sched_1"></td></tr>
          <tr><td>Wednesday</td><td id="sched_2"></td></tr>
          <tr><td>Thursday</td><td id="sched_3"></td></tr>
          <tr><td>Friday</td><td id="sched_4"></td></tr>
          <tr><td>Saturday</td><td id="sched_5"></td></tr>
          <tr><td>Sunday</td><td id="sched_6"></td></tr>
        </tbody>
      </table>

      <p class="withscript"><strong>All times are in UTC</strong></p>

      <p class="noscript"><a href="/schedule.json">click here to see the raw json since you don't have javascript enabled</a></p>
    </div>
  </div>
</div>

<footer>
  [
  <a href="/graphs/dashboard/db/lainon-life">graphs</a>
  /
  <a href="https://github.com/barrucadu/lainonlife">git</a>
  /
  <a href="/donate.html">donate</a>
  ]
</footer>
{% endblock %}
