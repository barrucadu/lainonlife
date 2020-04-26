{% extends "wrapper.tpl" %}

{% block title %}donate{% endblock %}

{% block body %}
<div class="box">
  <header>
    <h1>money, <strong>money,</strong> money</h1>
  </header>

  <p>
    The server costs {{ server_cost }}/month.
  </p>

  <p>
    You can send me money via <a href="https://paypal.me/barrucadu">PayPal</a>.
  </p>

  <p><a href="/">Return to the radio</a></p>
</div>
{% endblock %}
