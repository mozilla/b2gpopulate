#!/usr/bin/env python
#
# Before running this:
# 1) Install a B2G build with Marionette enabled
# 2) adb forward tcp:2828 tcp:2828

import json
from optparse import OptionParser
import os
import pkg_resources
import re
import shutil
import tempfile
import time
from zipfile import ZipFile

from marionette import Marionette
import mozdevice
import mozlog
from gaiatest import GaiaData
from gaiatest import GaiaDevice

DB_PRESET_TYPES = ['call', 'contact', 'event', 'message']
DB_PRESET_COUNTS = {
    'call': [0, 50, 100, 200, 500],
    'contact': [0, 200, 500, 1000, 2000],
    'event': [0, 900, 1300, 2400, 3200],
    'message': [0, 200, 500, 1000, 2000]}


class B2GPopulateError(Exception):
    def __init__(self, message):
        Exception.__init__(self, message)


class IncorrectCountError(B2GPopulateError):
    """Exception for a count being incorrect"""
    def __init__(self, file_type, expected, actual):
        Exception.__init__(
            self, 'Incorrect number of %s. Expected %s but found %s' % (
                file_type, expected, actual))


class InvalidCountError(B2GPopulateError):
    def __init__(self, data_type):
        Exception.__init__(
            self, 'Invalid value for %s count, use one of: %s' % (
                data_type, DB_PRESET_COUNTS[data_type]))


class B2GPopulate(object):

    PERSISTENT_STORAGE_PATH = '/data/local/storage/persistent'

    handler = mozlog.StreamHandler()
    handler.setFormatter(mozlog.MozFormatter(include_timestamp=True))
    logger = mozlog.getLogger('B2GPopulate', handler)

    def __init__(self, marionette, log_level='INFO', start_timeout=60):
        self.marionette = marionette
        self.data_layer = GaiaData(self.marionette)
        self.device = GaiaDevice(self.marionette)
        dm = mozdevice.DeviceManagerADB()
        self.device.add_device_manager(dm)

        self.logger.setLevel(getattr(mozlog, log_level.upper()))
        self.start_timeout = start_timeout

        if self.device.is_android_build:
            self.idb_dir = 'idb'
            for candidate in self.device.manager.listFiles(
                    '/'.join([self.PERSISTENT_STORAGE_PATH, 'chrome'])):
                if re.match('\d.*idb', candidate):
                    self.idb_dir = candidate
                    break

    def populate(self, call_count=None, contact_count=None, message_count=None,
                 music_count=None, picture_count=None, video_count=None,
                 event_count=None):

        restart = any([call_count, contact_count, message_count])

        if restart:
            self.logger.debug('Stopping B2G')
            self.device.stop_b2g()

        if call_count is not None:
            self.populate_calls(call_count, restart=False)

        if contact_count is not None:
            self.populate_contacts(contact_count, restart=False)

        if event_count is not None:
            self.populate_events(event_count, restart=False)

        if message_count is not None:
            self.populate_messages(message_count, restart=False)

        if restart:
            self.start_b2g()

        if music_count > 0:
            self.populate_music(music_count)

        if picture_count > 0:
            self.populate_pictures(picture_count)

        if video_count > 0:
            self.populate_videos(video_count)

    def populate_calls(self, count, restart=True):
        # only allow preset db values for calls
        db_counts = DB_PRESET_COUNTS['call']
        if not count in db_counts:
            raise InvalidCountError('call')
        self.logger.info('Populating %d calls' % count)
        db_counts.sort(reverse=True)
        for marker in db_counts:
            if count >= marker:
                key = 'communications.gaiamobile.org'
                local_id = json.loads(self.device.manager.pullFile(
                    '/data/local/webapps/webapps.json'))[key]['localId']
                db_zip_name = pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'dialerDb.zip']))
                db_name = 'dialerDb-%d.sqlite' % marker
                self.logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                destination = '/'.join([self.PERSISTENT_STORAGE_PATH,
                                        '%s+f+app+++%s' % (local_id, key),
                                        self.idb_dir,
                                        '2584670174dsitanleecreR.sqlite'])
                self.logger.debug('Pushing %s to %s' % (db, destination))
                self.device.push_file(db, destination=destination)
                self.logger.debug('Removing %s' % db)
                os.remove(db)
                if restart:
                    self.start_b2g()
                break

    def populate_contacts(self, count, restart=True, include_pictures=True):
        # only allow preset db values for contacts
        db_counts = DB_PRESET_COUNTS['contact']
        if not count in db_counts:
            raise InvalidCountError('contact')
        self.device.manager.removeDir('/'.join([
            self.PERSISTENT_STORAGE_PATH, 'chrome',
            self.idb_dir, '*csotncta*']))
        self.logger.info('Populating %d contacts' % count)
        db_counts.sort(reverse=True)
        for marker in db_counts:
            if count >= marker:
                db_zip_name = pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources',
                                                'contactsDb.zip']))
                db_name = 'contactsDb-%d.sqlite' % marker
                self.logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                destination = '/'.join([
                    self.PERSISTENT_STORAGE_PATH, 'chrome', self.idb_dir,
                    '3406066227csotncta.sqlite'])
                self.logger.debug('Pushing %s to %s' % (db, destination))
                self.device.push_file(db, destination=destination)
                self.logger.debug('Removing %s' % db)
                os.remove(db)
                if marker > 0 and include_pictures:
                    self.logger.debug('Adding contact pictures')
                    pictures_zip_name = pkg_resources.resource_filename(
                        __name__, os.path.sep.join(
                            ['resources', 'contactsPictures.zip']))
                    temp = tempfile.mkdtemp()
                    self.logger.debug('Extracting %s to %s' % (
                        pictures_zip_name, temp))
                    ZipFile(pictures_zip_name).extractall(temp)
                    destination = '/'.join([
                        self.PERSISTENT_STORAGE_PATH, 'chrome', self.idb_dir,
                        '3406066227csotncta'])
                    self.logger.debug('Pushing %s to %s' % (temp, destination))
                    self.device.manager.pushDir(temp, destination)
                    self.logger.debug('Removing %s' % temp)
                    shutil.rmtree(temp)
                if restart:
                    self.start_b2g()
                break

    def populate_events(self, count, restart=True):
        # only allow preset db values for events
        db_counts = DB_PRESET_COUNTS['event']
        if not count in db_counts:
            raise InvalidCountError('event')
        self.logger.info('Populating %d events' % count)
        db_counts.sort(reverse=True)
        for marker in db_counts:
            if count >= marker:
                key = 'calendar.gaiamobile.org'
                local_id = json.loads(self.device.manager.pullFile(
                    '/data/local/webapps/webapps.json'))[key]['localId']
                db_zip_name = pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources',
                                                'calendarDb.zip']))
                db_name = 'calendarDb-%d.sqlite' % marker
                self.logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                destination = '/'.join([self.PERSISTENT_STORAGE_PATH,
                                        '%s+f+app+++%s' % (local_id, key),
                                        self.idb_dir,
                                        '125582036br2agd-nceal.sqlite'])
                self.logger.debug('Pushing %s to %s' % (db, destination))
                self.device.push_file(db, destination=destination)
                self.logger.debug('Removing %s' % db)
                os.remove(db)
                if restart:
                    self.start_b2g()
                break

    def populate_messages(self, count, restart=True):
        # only allow preset db values for messages
        db_counts = DB_PRESET_COUNTS['message']
        if not count in db_counts:
            raise InvalidCountError('message')
        self.logger.info('Populating %d messages' % count)
        db_counts.sort(reverse=True)
        for marker in db_counts:
            if count >= marker:
                db_zip_name = pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'smsDb.zip']))
                db_name = 'smsDb-%d.sqlite' % marker
                self.logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                destination = '/'.join([
                    self.PERSISTENT_STORAGE_PATH, 'chrome', self.idb_dir,
                    '226660312ssm.sqlite'])
                self.logger.debug('Pushing %s to %s' % (db, destination))
                self.device.push_file(db, destination=destination)
                os.remove(db)
                if marker > 0:
                    self.logger.debug('Adding message attachments')
                    all_attachments_zip_name = pkg_resources.resource_filename(
                        __name__, os.path.sep.join(
                            ['resources', 'smsAttachments.zip']))
                    attachments_zip_name = 'smsAttachments-%d.zip' % marker
                    self.logger.debug('Extracting %s from %s' % (
                        attachments_zip_name, all_attachments_zip_name))
                    attachments_zip = ZipFile(
                        all_attachments_zip_name).extract(attachments_zip_name)
                    temp = tempfile.mkdtemp()
                    self.logger.debug('Extracting %s to %s' % (
                        attachments_zip, temp))
                    ZipFile(attachments_zip).extractall(temp)
                    destination = '/'.join([
                        self.PERSISTENT_STORAGE_PATH, 'chrome', self.idb_dir,
                        '226660312ssm'])
                    self.logger.debug('Pushing %s to %s' % (temp, destination))
                    self.device.manager.pushDir(temp, destination)
                    self.logger.debug('Removing %s' % temp)
                    shutil.rmtree(temp)
                    self.logger.debug('Removing %s' % attachments_zip)
                    os.remove(attachments_zip)
                if restart:
                    self.start_b2g()
                break

    def populate_music(self, count, source='MUS_0001.mp3',
                       destination='sdcard', tracks_per_album=10):
        self.remove_media('music')

        import math
        from mutagen.easyid3 import EasyID3
        music_file = pkg_resources.resource_filename(
            __name__, os.path.sep.join(['resources', source]))
        local_filename = music_file.rpartition(os.path.sep)[-1]

        # copy the mp3 file into a temp location
        with tempfile.NamedTemporaryFile() as local_copy:
            self.logger.debug('Creating copy of %s at %s' % (
                music_file, local_copy.name))
            local_copy.write(open(music_file).read())
            music_file = local_copy.name

            mp3 = EasyID3(music_file)
            album_count = math.ceil(float(count) / tracks_per_album)
            self.logger.info('Populating %d music files (%d album%s)' % (
                count, album_count, 's' if album_count > 1 else ''))

            for i in range(1, count + 1):
                album = math.ceil(float(i) / float(tracks_per_album))
                track = i - ((album - 1) * tracks_per_album)
                mp3['title'] = 'Track %d' % track
                mp3['artist'] = 'Artist %d' % album
                mp3['album'] = 'Album %d' % album
                mp3['tracknumber'] = str(track)
                mp3.save()
                remote_filename = '_%s.'.join(
                    iter(local_filename.split('.'))) % i
                remote_destination = os.path.join(destination, remote_filename)
                self.logger.debug('Pushing %s to %s' % (
                    music_file, remote_destination))
                self.device.push_file(music_file, 1, remote_destination)

    def populate_pictures(self, count, source='IMG_0001.jpg',
                          destination='sdcard/DCIM/100MZLLA'):
        self.populate_files('picture', source, count, destination)

    def populate_videos(self, count, source='VID_0001.3gp',
                        destination='sdcard/DCIM/100MZLLA'):
        self.populate_files('video', source, count, destination)

    def populate_files(self, file_type, source, count, destination=''):
        self.remove_media(file_type)

        self.logger.info('Populating %d %s files' % (count, file_type))
        source_file = pkg_resources.resource_filename(
            __name__, os.path.sep.join(['resources', source]))
        self.logger.debug('Pushing %d copies of %s to %s' % (
            count, source_file, destination))
        self.device.push_file(source_file, count, destination)

    def remove_media(self, file_type):
        if self.device.is_android_build:
            files = getattr(self.data_layer, '%s_files' % file_type) or []
            if len(files) > 0:
                self.logger.info('Removing %d %s files' % (
                    len(files), file_type))
                for filename in files:
                    self.logger.debug('Removing %s' % filename)
                    self.device.manager.removeFile(filename)
                # TODO Wait for files to be deleted
                time.sleep(5)
                files = getattr(self.data_layer, '%s_files' % file_type) or []
            if not len(files) == 0:
                raise IncorrectCountError(
                    '%s files' % file_type, 0, len(files))

    def start_b2g(self):
        self.logger.debug('Starting B2G')
        self.device.start_b2g(self.start_timeout * 1000)  # convert to ms
        self.data_layer = GaiaData(self.marionette)


def cli():
    parser = OptionParser(usage='%prog [options]')
    parser.add_option(
        '--log-level',
        action='store',
        dest='log_level',
        default='INFO',
        metavar='str',
        help='threshold for log output (default: %default)')
    parser.add_option(
        '--start-timeout',
        action='store',
        type=int,
        dest='start_timeout',
        default=60,
        metavar='int',
        help='b2g start timeout in seconds (default: %default)')
    parser.add_option(
        '--calls',
        action='store',
        type=int,
        dest='call_count',
        metavar='int',
        help='number of calls to create. must be one of: %s' %
             DB_PRESET_COUNTS['call'])
    parser.add_option(
        '--contacts',
        action='store',
        type=int,
        dest='contact_count',
        metavar='int',
        help='number of contacts to create. must be one of: %s' %
             DB_PRESET_COUNTS['contact'])
    parser.add_option(
        '--events',
        action='store',
        type=int,
        dest='event_count',
        metavar='int',
        help='number of events to create. must be one of: %s' %
             DB_PRESET_COUNTS['event'])
    parser.add_option(
        '--messages',
        action='store',
        type=int,
        dest='message_count',
        metavar='int',
        help='number of messages to create. must be one of: %s' %
             DB_PRESET_COUNTS['message'])
    parser.add_option(
        '--music',
        action='store',
        type=int,
        dest='music_count',
        metavar='int',
        help='number of music files to create')
    parser.add_option(
        '--pictures',
        action='store',
        type=int,
        dest='picture_count',
        metavar='int',
        help='number of pictures to create')
    parser.add_option(
        '--videos',
        action='store',
        type=int,
        dest='video_count',
        metavar='int',
        help='number of videos to create')

    options, args = parser.parse_args()

    data_types = ['call', 'contact', 'event', 'message', 'music', 'picture',
                  'video']
    for data_type in data_types:
        count = getattr(options, '%s_count' % data_type)
        if count and not count >= 0:
            parser.print_usage()
            print 'Invalid value for %s count!' % data_type
            parser.exit()

    counts = [getattr(options, '%s_count' % data_type) for
              data_type in data_types]
    if not len([count for count in counts if count >= 0]) > 0:
        parser.print_usage()
        print 'Must specify at least one item to populate'
        parser.exit()

    # only allow preset db values for calls and messages
    for data_type in DB_PRESET_TYPES:
        count = getattr(options, '%s_count' % data_type)
        if count and not count in DB_PRESET_COUNTS[data_type]:
            raise InvalidCountError(data_type)

    # TODO command line option for address
    marionette = Marionette(host='localhost', port=2828, timeout=180000)
    marionette.start_session()
    B2GPopulate(marionette, options.log_level, options.start_timeout).populate(
        options.call_count,
        options.contact_count,
        options.message_count,
        options.music_count,
        options.picture_count,
        options.video_count,
        options.event_count)


if __name__ == '__main__':
    cli()
