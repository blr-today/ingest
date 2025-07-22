#!/bin/bash
# Install latest release of SQLite using the amalgamation source code.

OLDDIR=$(pwd)
cd /tmp
DOWNLOAD_URL=https://sqlite.org/2025/sqlite-amalgamation-3500300.zip
wget -qnc "$DOWNLOAD_URL"
rm -rf sqlite-amalgamation-3500300 sqlite
unzip sqlite-amalgamation-3500300.zip
mv sqlite-amalgamation-3500300 sqlite
cd sqlite
# Compile options from Arch Linux
gcc -shared -fPIC -o libsqlite.so \
	-DSQLITE_ENABLE_COLUMN_METADATA=1 \
    -DSQLITE_ENABLE_UNLOCK_NOTIFY \
    -DSQLITE_ENABLE_DBSTAT_VTAB=1 \
    -DSQLITE_ENABLE_FTS3_TOKENIZER=1 \
    -DSQLITE_ENABLE_FTS3_PARENTHESIS \
    -DSQLITE_SECURE_DELETE \
    -DSQLITE_ENABLE_STMTVTAB \
    -DSQLITE_ENABLE_STAT4 \
    -DSQLITE_MAX_VARIABLE_NUMBER=250000 \
    -DSQLITE_MAX_EXPR_DEPTH=10000 \
    -DSQLITE_ENABLE_MATH_FUNCTIONS \
	-DSQLITE_THREADSAFE=1 \
	sqlite3.c
cp libsqlite.so $OLDDIR
cd -
