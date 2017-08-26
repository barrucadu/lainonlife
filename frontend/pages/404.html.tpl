{% extends "wrapper.tpl" %}

{% block title %}404{% endblock %}

{% block head %}
<style type="text/css">
  body { background: url("/404/background.gif") center center / cover no-repeat fixed; text-align: center; }
</style>
{% endblock %}

{% block body %}
<h1 id="message">THIS IS A 404</h1>
<audio autoplay loop>
  <source src="/404/duvet.ogg" type="audio/ogg" />
  <source src="/404/duvet.mp3" type="audio/mpeg" />
</audio>
{% endblock %}
