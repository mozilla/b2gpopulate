# Change Log

## 0.12
* Bumped gaiatest dependency to 0.20
* Add option to skip contact pictures
* Allow b2gpopulate to be instantiated multiple times
* Replaced custom log formatter with timestamped mozlog formatter

## 0.11
* Bumped gaiatest dependency to 0.19

## 0.10
* Add support for populating calendar events
* Add contacts pictures
* Only allow preset database values for contacts
* Replace progressbar with mozlog
* Allow use of b2gpopulate as a module
* Only restart once when pushing multiple databases
* Add custom exceptions
* Remove type specific media files before populating instead of all media files

## 0.9
* Bug 916064 - Update to support persistent storage path changes

## 0.8
* Push databases to appropriate idb directory
* Add support for populating call history
* Add support for MMS messages

## 0.7.1
* Avoid modifying the packaged MP3 file. #2

## 0.7
* Updated databases for latest B2G (for v1.0.1 use 0.6.1)
* Show progress when removing media and fail if unsuccessful

## 0.6.1
* Avoid pinning to a specific mutagen release

## 0.6
* Split music into albums with 10 tracks per album

## 0.5
* Use prebuilt contacts databases for faster population
* Add support for populating SMS messages

## 0.4
* Fixed more issues with package resources

## 0.3
* Fixes issues with package resources

## 0.2
* Improved timeouts when removing contacts

## 0.1
* Initial release
