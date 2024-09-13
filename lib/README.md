GitHub Actions uses Ubuntu 22.04, which ships sqlite 3.31, while we need
3.38

https://sqlite.org/json1.html#jptr says

Beginning with SQLite version 3.38.0 (2022-02-22), the -> and ->> operators are available for extracting subcomponents of JSON.

Didn't feel like compiling libsqlite, so we ship the libsqlite.so from ubuntu 24.04.

comes from libsqlite3-0_3.45.1-1ubuntu2_amd64.deb

downloaded from https://packages.ubuntu.com/noble/amd64/libsqlite3-0/download

Usable in Python by using LD_PRELOAD if needed
