{% extends "wrapper.tpl" %}

{% block title %}dj login{% endblock %}

{% block body %}
<form action="" method=post class="form-horizontal">
  <h2>sign in</h2>
  <div class="control-group">
    <div class="controls">
      <input type="text" id="username" name="username" class="input-xlarge"
             placeholder="username" required>
    </div>
  </div>

  <div class="control-group">
    <div class="controls">
      <input type="password" id="password" name="password" class="input-xlarge"
             placeholder="password" required>
        </div>
  </div>

  <div class="control-group">
    <div class="controls">
      <button type="submit" class="btn btn-success">go</button>
    </div>
  </div>
</form>
{% endblock %}
