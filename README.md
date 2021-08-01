[lain.void.yt](lain.void.yt)
===============

Online radio for lainons. Original instance: [lainon.life](lainon.life) by [barrucadu](https://github.com/barrucadu/lainonlife)

Assumptions
-----------

There are some assumptions in the code you might have to fix before
deploying for real elsewhere:

- `backend.py` assumes that it has write access to the `upload` directory.
- `schedule.py` assumes that bumps are in the album "Lainchan Radio Transitions".

These shouldn't really matter for development.  Some things might not
work properly, that's it.  There might be more things.

Configuration
-------------

There are a few files you might reasonably want to edit if you deploy
this code:

- `config.json`, the list of channels, [MPD][] details, and frontend
  asset template details.

The [lainon.life][] server is running [NixOS][], and the entire system
configuration (sans passwords) [is on github][nixfiles].

For those who don't read Nix, the `examples/` directory contains
sample configuration for [nginx][], [Icecast][], [MPD][], [Crontab][], and [Systemd][].

For those that use debian 10 to host lainonlife, you can follow this [tutorial](https://blog.void.yt/servers/lainradio/index.html).

Usage
-----

0. Configure your webserver.

    See the `examples/` directory for help.

1. Build the frontend assets.

    ```
    $ cd frontend
    $ ./run.sh ../config.json
    ```

    If all goes well, the directory `_site` now contains all the
    frontend assets.

2. Put the frontend assets where you told the server they would be.

    ```
    $ cp -r frontend/_site/* /srv/http
    ```

3. Start the backend on the port you told the server it would be.

    ```
    $ cd backend
    $ CONFIG=../config.json HTTP_DIR=/srv/http PORT=5000 ./run.sh
    ```

Frontend development
--------------------

Frontend development is setup with [pipenv](https://pipenv.pypa.io).
Initially you have to run `pipenv install` in the `frontend` subdirectory.

There are 3 essential scripts for development:
- build: builds the static site, its out put can be found in `frontend/_site`
- watch: watches the source files for changes and rebuilds
- serve: watches the source files and also run a local webserver on localhost

You can run these scripts like so: `pipenv run build`

I want to help!
---------------

Great!  See the open issues.  You can also find me on irc.lainchan.org.


[Icecast]:     http://icecast.org/
[MPD]:         https://www.musicpd.org/
[lainon.life]: https://lainon.life/
[NixOS]:       https://nixos.org/
[nixfiles]:    https://github.com/barrucadu/nixfiles
[nginx]:       https://www.nginx.com/
[Crontab]:     https://crontab.guru/
[Systemd]:     https://wiki.debian.org/systemd/Services
