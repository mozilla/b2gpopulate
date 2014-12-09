#!/usr/bin/env python
#
# Before running this:
# 1) Install a B2G build with Marionette enabled
# 2) adb forward tcp:2828 tcp:2828

import argparse
import json
import os
import pkg_resources
import posixpath
import re
import shutil
import sys
import tempfile
from zipfile import ZipFile

from marionette import Marionette
import mozdevice
import mozlog
from mozlog import structured
from gaiatest import GaiaData
from gaiatest import GaiaDevice

WORKLOADS = {
    'empty': {
        'call': 0,
        'contact': 0,
        'message': 0,
        'music': 0,
        'picture': 0,
        'video': 0,
        'event': 0},
    'light': {
        'call': 50,
        'contact': 200,
        'message': 200,
        'music': 20,
        'picture': 20,
        'video': 5,
        'event': 900},
    'medium': {
        'call': 100,
        'contact': 500,
        'message': 500,
        'music': 50,
        'picture': 50,
        'video': 10,
        'event': 1300},
    'heavy': {
        'call': 200,
        'contact': 1000,
        'message': 1000,
        'music': 100,
        'picture': 100,
        'video': 20,
        'event': 2400},
    'x-heavy': {
        'call': 500,
        'contact': 2000,
        'message': 2000,
        'music': 250,
        'picture': 250,
        'video': 50,
        'event': 3200}
}


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
                data_type,
                sorted([WORKLOADS[k][data_type] for k in WORKLOADS.keys()])))


class B2GPopulate(object):

    STORAGE_PATH = '/data/local/storage'

    handler = mozlog.StreamHandler()
    handler.setFormatter(mozlog.MozFormatter(include_timestamp=True))
    logger = mozlog.getLogger('B2GPopulate', handler)

    def __init__(self, marionette, start_timeout=60, device_serial=None):
        self.marionette = marionette
        self.data_layer = GaiaData(self.marionette)
        dm = mozdevice.DeviceManagerADB(deviceSerial=device_serial)
        self.device = GaiaDevice(self.marionette, manager=dm)

        self._logger = structured.get_default_logger(component='b2gpopulate')
        if not self._logger:
            self._logger = mozlog.getLogger('b2gpopulate')
        self.start_timeout = start_timeout

        if self.device.is_android_build:
            self.idb_dir = 'idb'
            for candidate in self.device.file_manager.list_items(
                    posixpath.join(self.STORAGE_PATH, 'permanent', 'chrome')):
                if re.match('\d.*idb', candidate):
                    self.idb_dir = candidate
                    break

    def populate(self, call_count=None, contact_count=None, message_count=None,
                 music_count=None, picture_count=None, video_count=None,
                 event_count=None):

        restart = any([i is not None for i in [
            call_count, contact_count, event_count, message_count]])

        if restart:
            self._logger.debug('Stopping B2G')
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

        if music_count is not None:
            self.populate_music(music_count)

        if picture_count is not None:
            self.populate_pictures(picture_count)

        if video_count is not None:
            self.populate_videos(video_count)

    def populate_calls(self, count, restart=True):
        # only allow preset db values for calls
        db_counts = [WORKLOADS[k]['call'] for k in WORKLOADS.keys()]
        if count not in db_counts:
            raise InvalidCountError('call')
        self._logger.info('Populating %d calls' % count)
        db_counts.sort(reverse=True)
        for marker in db_counts:
            if count >= marker:
                key = 'communications.gaiamobile.org'
                local_id = json.loads(self.device.manager.pullFile(
                    '/data/local/webapps/webapps.json'))[key]['localId']
                db_zip_name = pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'dialerDb.zip']))
                db_name = 'dialerDb-%d.sqlite' % marker
                self._logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                destination = posixpath.join(self.STORAGE_PATH, 'default',
                                             '%s+f+app+++%s' % (local_id, key),
                                             self.idb_dir,
                                             '2584670174dsitanleecreR.sqlite')
                self._logger.debug('Pushing %s to %s' % (db, destination))
                self.device.manager.pushFile(db, destination)
                self._logger.debug('Removing %s' % db)
                os.remove(db)
                if restart:
                    self.start_b2g()
                break

    def populate_contacts(self, count, restart=True, include_pictures=True):
        # only allow preset db values for contacts
        db_counts = [WORKLOADS[k]['contact'] for k in WORKLOADS.keys()]
        if count not in db_counts:
            raise InvalidCountError('contact')
        path = posixpath.join(self.STORAGE_PATH, 'permanent', 'chrome', self.idb_dir)
        self.device.file_manager.remove(posixpath.join(path, '*csotncta*'))
        self._logger.info('Populating %d contacts' % count)
        db_counts.sort(reverse=True)
        for marker in db_counts:
            if count >= marker:
                db_zip_name = pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources',
                                                'contactsDb.zip']))
                db_name = 'contactsDb-%d.sqlite' % marker
                self._logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                destination = posixpath.join(path, '3406066227csotncta.sqlite')
                self._logger.debug('Pushing %s to %s' % (db, destination))
                self.device.manager.pushFile(db, destination)
                self._logger.debug('Removing %s' % db)
                os.remove(db)
                if marker > 0 and include_pictures:
                    self._logger.debug('Adding contact pictures')
                    pictures_zip_name = pkg_resources.resource_filename(
                        __name__, os.path.sep.join(
                            ['resources', 'contactsPictures.zip']))
                    temp = tempfile.mkdtemp()
                    self._logger.debug('Extracting %s to %s' % (
                        pictures_zip_name, temp))
                    ZipFile(pictures_zip_name).extractall(temp)
                    destination = posixpath.join(path, '3406066227csotncta.files')
                    self._logger.debug('Pushing %s to %s' % (temp, destination))
                    self.device.manager.pushDir(temp, destination)
                    self._logger.debug('Removing %s' % temp)
                    shutil.rmtree(temp)
                if restart:
                    self.start_b2g()
                break

    def populate_events(self, count, restart=True):
        # only allow preset db values for events
        db_counts = [WORKLOADS[k]['event'] for k in WORKLOADS.keys()]
        if count not in db_counts:
            raise InvalidCountError('event')
        self._logger.info('Populating %d events' % count)
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
                self._logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                destination = posixpath.join(self.STORAGE_PATH, 'default',
                                             '%s+f+app+++%s' % (local_id, key),
                                             self.idb_dir,
                                             '125582036br2agd-nceal.sqlite')
                self._logger.debug('Pushing %s to %s' % (db, destination))
                self.device.manager.pushFile(db, destination)
                self._logger.debug('Removing %s' % db)
                os.remove(db)
                if restart:
                    self.start_b2g()
                break

    def populate_messages(self, count, restart=True):
        # only allow preset db values for messages
        db_counts = [WORKLOADS[k]['message'] for k in WORKLOADS.keys()]
        if count not in db_counts:
            raise InvalidCountError('message')
        self._logger.info('Populating %d messages' % count)
        db_counts.sort(reverse=True)
        for marker in db_counts:
            if count >= marker:
                db_zip_name = pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'smsDb.zip']))
                db_name = 'smsDb-%d.sqlite' % marker
                self._logger.debug('Extracting %s from %s' % (
                    db_name, db_zip_name))
                db = ZipFile(db_zip_name).extract(db_name)
                if restart:
                    self.device.stop_b2g()
                path = posixpath.join(self.STORAGE_PATH, 'permanent', 'chrome', self.idb_dir)
                destination = posixpath.join(path, '226660312ssm.sqlite')
                self._logger.debug('Pushing %s to %s' % (db, destination))
                self.device.manager.pushFile(db, destination)
                os.remove(db)
                if marker > 0:
                    self._logger.debug('Adding message attachments')
                    all_attachments_zip_name = pkg_resources.resource_filename(
                        __name__, os.path.sep.join(
                            ['resources', 'smsAttachments.zip']))
                    attachments_zip_name = 'smsAttachments-%d.zip' % marker
                    self._logger.debug('Extracting %s from %s' % (
                        attachments_zip_name, all_attachments_zip_name))
                    attachments_zip = ZipFile(
                        all_attachments_zip_name).extract(attachments_zip_name)
                    temp = tempfile.mkdtemp()
                    self._logger.debug('Extracting %s to %s' % (
                        attachments_zip, temp))
                    ZipFile(attachments_zip).extractall(temp)
                    destination = posixpath.join(path, '226660312ssm.files')
                    self._logger.debug('Pushing %s to %s' % (temp, destination))
                    self.device.manager.pushDir(temp, destination)
                    self._logger.debug('Removing %s' % temp)
                    shutil.rmtree(temp)
                    self._logger.debug('Removing %s' % attachments_zip)
                    os.remove(attachments_zip)
                if restart:
                    self.start_b2g()
                break

    def populate_music(self, count, source='MUS_0001.mp3',
                       tracks_per_album=10):
        self.remove_media('music')

        import math
        from mutagen.easyid3 import EasyID3
        music_file = pkg_resources.resource_filename(
            __name__, os.path.sep.join(['resources', source]))
        local_filename = music_file.rpartition(os.path.sep)[-1]

        # copy the mp3 file into a temp location
        with tempfile.NamedTemporaryFile() as local_copy:
            self._logger.debug('Creating copy of %s at %s' % (
                music_file, local_copy.name))
            local_copy.write(open(music_file).read())
            music_file = local_copy.name

            mp3 = EasyID3(music_file)
            album_count = math.ceil(float(count) / tracks_per_album)
            self._logger.info('Populating %d music files (%d album%s)' % (
                count, album_count, '' if album_count == 1 else 's'))

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
                remote_destination = posixpath.join(
                    self.device.manager.deviceRoot, remote_filename)
                self._logger.debug('Pushing %s to %s' % (
                    music_file, remote_destination))
                self.device.manager.pushFile(music_file, remote_destination)

    def populate_pictures(self, count, source='IMG_0001.jpg',
                          destination='DCIM/100MZLLA'):
        self.populate_files('picture', source, count, destination)

    def populate_videos(self, count, source='VID_0001.3gp',
                        destination='DCIM/100MZLLA'):
        self.populate_files('video', source, count, destination)

    def populate_files(self, file_type, source, count, destination=''):
        destination = posixpath.join(self.device.manager.deviceRoot, destination)
        self.remove_media(file_type)

        self._logger.info('Populating %d %s files' % (count, file_type))
        if count > 0:
            source_file = pkg_resources.resource_filename(
                __name__, os.path.sep.join(['resources', source]))
            self._logger.debug('Pushing %d copies of %s to %s' % (
                count, source_file, destination))
            self.device.file_manager.push_file(source_file, destination, count)

    def remove_media(self, file_type):
        if self.device.is_android_build:
            files = getattr(self.data_layer, '%s_files' % file_type) or []
            if len(files) > 0:
                self._logger.info('Removing %d %s files' % (
                    len(files), file_type))
                volumes = self.get_volumes()
                for filename in files:
                    # Get the actual location of the file
                    parts = filename.strip(posixpath.sep).partition(posixpath.sep)
                    path = posixpath.join(volumes[parts[0]], parts[2])
                    self._logger.debug('Removing %s' % path)
                    self.device.file_manager.remove(path)
                files = getattr(self.data_layer, '%s_files' % file_type) or []
            if not len(files) == 0:
                raise IncorrectCountError(
                    '%s files' % file_type, 0, len(files))

    def get_volumes(self):
        version = int(self.device.manager.shellCheckOutput(
            ['getprop', 'ro.build.version.sdk']))
        # Version > 17 introduced a new column
        start = version > 17 and 2 or 1
        end = start + 2
        vlist = self.device.manager.shellCheckOutput(['vdc', 'volume', 'list'])
        return dict([v.split()[start:end] for v in vlist.splitlines()[:-1]])

    def start_b2g(self):
        self._logger.debug('Starting B2G')
        self.device.start_b2g(self.start_timeout)
        self.data_layer = GaiaData(self.marionette)


def cli():
    parser = argparse.ArgumentParser(
        description='Content population tool for Firefox OS')
    parser.add_argument(
        '--address',
        default='localhost:2828',
        help='address of marionette server (default: %(default)s)')
    parser.add_argument(
        '--device-serial',
        metavar='SERIAL',
        help='serial identifier of device to target')
    parser.add_argument(
        '--start-timeout',
        type=int,
        default=60,
        metavar='TIMEOUT',
        help='b2g start timeout in seconds (default: %(default)s)')
    parser.add_argument(
        '--calls',
        type=int,
        dest='call_count',
        metavar='CALLS',
        help='number of calls to create. must be one of: %s' %
             sorted([WORKLOADS[k]['call'] for k in WORKLOADS.keys()]))
    parser.add_argument(
        '--contacts',
        type=int,
        dest='contact_count',
        metavar='CONTACTS',
        help='number of contacts to create. must be one of: %s' %
             sorted([WORKLOADS[k]['contact'] for k in WORKLOADS.keys()]))
    parser.add_argument(
        '--events',
        type=int,
        dest='event_count',
        metavar='EVENTS',
        help='number of events to create. must be one of: %s' %
             sorted([WORKLOADS[k]['event'] for k in WORKLOADS.keys()]))
    parser.add_argument(
        '--messages',
        type=int,
        dest='message_count',
        metavar='MESSAGES',
        help='number of messages to create. must be one of: %s' %
             sorted([WORKLOADS[k]['message'] for k in WORKLOADS.keys()]))
    parser.add_argument(
        '--music',
        type=int,
        dest='music_count',
        metavar='MUSIC',
        help='number of music files to create')
    parser.add_argument(
        '--pictures',
        type=int,
        dest='picture_count',
        metavar='PICTURES',
        help='number of pictures to create')
    parser.add_argument(
        '--videos',
        type=int,
        dest='video_count',
        metavar='VIDEOS',
        help='number of videos to create')
    parser.add_argument(
        '--workload',
        metavar='WORKLOAD',
        choices=sorted(WORKLOADS, key=WORKLOADS.__getitem__),
        help='type of workload to create. must be one of: %s' %
             sorted(WORKLOADS, key=WORKLOADS.__getitem__))
    structured.commandline.add_logging_group(parser)

    args = parser.parse_args()
    structured.commandline.setup_logging(
        'b2gpopulate', args, {'mach': sys.stdout})

    data_types = WORKLOADS['empty'].keys()
    for data_type in data_types:
        count = getattr(args, '%s_count' % data_type)
        if count and not count >= 0:
            parser.print_usage()
            print 'Invalid value for %s count!' % data_type
            parser.exit()

    counts = [getattr(args, '%s_count' % data_type) for
              data_type in data_types]
    if not len([count for count in counts if count >= 0]) > 0:
        if args.workload is None:
            parser.print_usage()
            print 'Must specify at least one item to populate'
            parser.exit()
    else:
        if args.workload is not None:
            parser.print_usage()
            print 'Please specify either a workload or individual values'
            parser.exit()

    # only allow preset values for calls, messages, contacts, events
    for data_type in ['call', 'message', 'contact', 'event']:
        count = getattr(args, '%s_count' % data_type)
        preset_counts = [WORKLOADS[k][data_type] for k in WORKLOADS.keys()]
        if count and count not in preset_counts:
            raise InvalidCountError(data_type)

    try:
        host, port = args.address.split(':')
    except ValueError:
        raise B2GPopulateError('--address must be in the format host:port')

    marionette = Marionette(host=host, port=int(port), timeout=180000)
    marionette.start_session()
    b2gpopulate = B2GPopulate(marionette,
                              start_timeout=args.start_timeout,
                              device_serial=args.device_serial)

    if args.workload is None:
        b2gpopulate.populate(
            args.call_count,
            args.contact_count,
            args.message_count,
            args.music_count,
            args.picture_count,
            args.video_count,
            args.event_count)
    else:
        b2gpopulate.populate(
            WORKLOADS[args.workload]['call'],
            WORKLOADS[args.workload]['contact'],
            WORKLOADS[args.workload]['message'],
            WORKLOADS[args.workload]['music'],
            WORKLOADS[args.workload]['picture'],
            WORKLOADS[args.workload]['video'],
            WORKLOADS[args.workload]['event'])


if __name__ == '__main__':
    cli()
