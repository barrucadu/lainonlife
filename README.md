[lainon.life][]
===============

Online radio for lainons.

Assumptions
-----------

There are some assumptions in the code you might have to fix before
deploying for real elsewhere:

- `backend.py` assumes that it has write access to the `upload` directory.
- `metrics.py` probably assumes a lot about permissions.
- `radio.js` assumes [Icecast][] is accessible at /radio/.
- `schedule.py` assumes that bumps are in the album "Lainchan Radio Transitions".

These shouldn't really matter for development.  Some things might not
work properly, that's it.

Configuration
-------------

There are a few files you might reasonably want to edit if you deploy
this code:

- `channels.json`, the list of channels and [MPD][] details.
- `frontend/Main.hs`, the `config` value at the top of the file.
- `frontend/static/schedule.json`, the live broadcast schedule.

The [lainon.life][] server is running [NixOS][], and the entire system
configuration (sans passwords) [is on github][nixfiles].

For those who don't read Nix, the `examples/` directory contains
sample configuration for [nginx][], [Icecast][], and [MPD][].

Usage
-----

0. Configure your webserver.

    See the `examples/` directory for help.

1. Build the frontend assets.

    You need [stack][]; or [hpack][], [cabal-install][], and [GHC][].

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


[Icecast]:       http://icecast.org/
[MPD]:           https://www.musicpd.org/
[lainon.life]:   https://lainon.life/
[NixOS]:         https://nixos.org/
[nixfiles]:      https://github.com/barrucadu/nixfiles
[nginx]:         https://www.nginx.com/
[stack]:         https://www.haskellstack.org/
[hpack]:         https://github.com/sol/hpack
[cabal-install]: https://www.haskell.org/cabal/
[GHC]:           https://www.haskell.org/ghc/
