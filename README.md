# b2gpopulate

b2gpopulate is a tool to populate a
[Firefox OS](https://developer.mozilla.org/en-US/docs/Mozilla/Firefox_OS)
device with content.

## Requirements

Your device must be running a build of Firefox OS with
[Marionette](https://developer.mozilla.org/docs/Marionette) enabled.

## Installation

Installation is simple:

    pip install b2gpopulate

If you anticipate modifying b2gpopulate, you can instead:

    git clone git://github.com/davehunt/b2gpopulate.git
    cd b2gpopulate
    python setup.py develop

## Running

    b2gpopulate --contacts=500 --music=100 --pictures=100 --videos=100
