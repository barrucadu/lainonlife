lainon.life
===========

Online radio for lainons.

Assumptions
-----------

There are some assumptions in the code you might have to fix before
deploying for real elsewhere:

- `backend.py` assumes that it has write access to the `upload` directory.
- `backend.py` assumes that there are four [MPD](https://www.musicpd.org/) instances running on ports 6600 to 6603.
- `metrics.py` probably assumes a lot about permissions.
- `radio.js` assumes [Icecast](http://icecast.org/) is accessible at /radio/.
- `schedule.py` assumes that bumps are in the album "Lainchan Radio Transitions".

These shouldn't really matter for development.  Some things might not
work properly, that's it.

Usage
-----

0. Configure your webserver.

    You'll need to configure it to both serve static files (probably
    from some directory under `/srv/http` or `/var/www`) and proxy
    unknown requests to the backend (which will be running on some
    port you choose now).

    Here's an example for [nginx](https://www.nginx.com/),
    serving files from `/srv/http` and using port 5000 for the backend.

    ```
    server {
      listen 80 default_server;
      listen [::]:80 default_server;

      root /srv/http;

      location / {
        try_files $uri $uri/ @script;
      }

      location @script {
        proxy_pass http://localhost:5000;
      }
    }
    ```

1. Build the frontend assets.

    You need [stack](https://www.haskellstack.org/); or
    [hpack](https://github.com/sol/hpack),
    [cabal-install](https://www.haskell.org/cabal/), and
    [GHC](https://www.haskell.org/ghc/).

    ```
    $ cd frontend
    $ stack build
    $ stack exec frontend build
    ```

    If all goes well, the directory `_site` now contains all the frontend assets.

    This will take a while the first time because GHC is slow and
    Haskell things pull in a lot of dependencies.

2. Put the frontend assets where you told the server they would be.

    ```
    $ cp -r frontend/_site/* /srv/http
    ```

3. Start the backend on the port you told the server it would be.

    ```
    $ ./misc/backend.py --http-dir=/srv/http 5000
    ```


Bash, Haskell, AND Python?
--------------------------

I like bash and Python for small things, where bash beats Python into
the ground for things which don't really require any logic.  I like
Haskell for everything else.


I want to help!
---------------

Great!  See the open issues.  You can also find me on irc.lainchan.org.
