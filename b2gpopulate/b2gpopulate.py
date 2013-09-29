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
from zipfile import ZipFile

from progressbar import Counter
from progressbar import ProgressBar

from marionette import Marionette
from gaiatest import GaiaData
from gaiatest import GaiaDevice

DB_PRESET_TYPES = ['call', 'message']
DB_PRESET_COUNTS = {
    'call': [0, 50, 100, 200, 500],
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


class B2GPopulate:

    PERSISTENT_STORAGE_PATH = '/data/local/storage/persistent'

    def __init__(self, marionette):
        self.marionette = marionette
        self.data_layer = GaiaData(self.marionette)
        self.device = GaiaDevice(self.marionette)

        if self.device.is_android_build:
            self.idb_dir = 'idb'
            for candidate in self.device.manager.listFiles(
                    '/'.join([self.PERSISTENT_STORAGE_PATH, 'chrome'])):
                if re.match('\d.*idb', candidate):
                    self.idb_dir = candidate
                    break

    def populate(self, call_count=None, contact_count=None, message_count=None,
                 music_count=None, picture_count=None, video_count=None):

        if call_count is not None:
            self.populate_calls(call_count)

        if contact_count is not None:
            self.populate_contacts(contact_count)

        if message_count is not None:
            self.populate_messages(message_count)

        if music_count > 0:
            self.populate_music(music_count)

        if picture_count > 0:
            self.populate_pictures(picture_count)

        if video_count > 0:
            self.populate_videos(video_count)

    def populate_calls(self, count):
        # only allow preset db values for calls
        db_call_counts = [0, 50, 100, 200, 500]
        if not count in db_call_counts:
            raise InvalidCountError('call')
        progress = ProgressBar(widgets=[
            'Populating Calls: ', '[', Counter(), '/%d] ' % count],
            maxval=count)
        progress.start()
        db_call_counts.sort(reverse=True)
        for marker in db_call_counts:
            if count >= marker:
                key = 'communications.gaiamobile.org'
                local_id = json.loads(self.device.manager.pullFile(
                    '/data/local/webapps/webapps.json'))[key]['localId']
                db_zip = ZipFile(pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'dialerDb.zip'])))
                db = db_zip.extract('dialerDb-%d.sqlite' % marker)
                self.device.stop_b2g()
                destination = '/'.join([self.PERSISTENT_STORAGE_PATH,
                                        '%s+f+app+++%s' % (local_id, key),
                                        self.idb_dir,
                                        '2584670174dsitanleecreR.sqlite'])
                self.device.push_file(db, destination=destination)
                os.remove(db)
                self.start_b2g()
                progress.update(marker)
                progress.finish()
                break

    def populate_contacts(self, count):
        progress = ProgressBar(widgets=[
            'Populating Contacts: ', '[', Counter(), '/%d] ' % count],
            maxval=count)
        progress.start()
        for marker in [2000, 1000, 500, 200, 0]:
            if count >= marker:
                db_zip = ZipFile(pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources',
                                                'contactsDb.zip'])))
                db = db_zip.extract('contactsDb-%d.sqlite' % marker)
                self.device.stop_b2g()
                self.device.push_file(
                    db, destination='/'.join([
                        self.PERSISTENT_STORAGE_PATH, 'chrome', self.idb_dir,
                        '3406066227csotncta.sqlite']))
                os.remove(db)
                self.start_b2g()
                progress.update(marker)
                remainder = count - marker
                if remainder > 0:
                    from gaiatest.mocks.mock_contact import MockContact
                    for i in range(remainder):
                        GaiaData(self.marionette).insert_contact(MockContact())
                        progress.update(marker + (i + 1))
                progress.finish()
                break

    def populate_messages(self, count):
        # only allow preset db values for messages
        db_message_counts = [0, 200, 500, 1000, 2000]
        if not count in db_message_counts:
            raise InvalidCountError('message')
        progress = ProgressBar(widgets=[
            'Populating Messages: ', '[', Counter(), '/%d] ' % count],
            maxval=count)
        progress.start()
        db_message_counts.sort(reverse=True)
        for marker in db_message_counts:
            if count >= marker:
                db_zip = ZipFile(pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'smsDb.zip'])))
                db = db_zip.extract('smsDb-%d.sqlite' % marker)
                self.device.stop_b2g()
                self.device.push_file(
                    db, destination='/'.join([
                        self.PERSISTENT_STORAGE_PATH, 'chrome', self.idb_dir,
                        '226660312ssm.sqlite']))
                os.remove(db)
                if marker > 0:
                    all_attachments_zip = ZipFile(
                        pkg_resources.resource_filename(
                            __name__, os.path.sep.join(
                                ['resources', 'smsAttachments.zip'])))
                    attachments_zip = all_attachments_zip.extract(
                        'smsAttachments-%d.zip' % marker)
                    local_path = tempfile.mkdtemp()
                    ZipFile(attachments_zip).extractall(local_path)
                    self.device.manager.pushDir(local_path, '/'.join([
                        self.PERSISTENT_STORAGE_PATH, 'chrome', self.idb_dir,
                        '226660312ssm']))
                    shutil.rmtree(local_path)
                    os.remove(attachments_zip)
                self.start_b2g()
                progress.update(marker)
                progress.finish()
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
            local_copy.write(open(music_file).read())
            music_file = local_copy.name

            mp3 = EasyID3(music_file)

            progress = ProgressBar(widgets=[
                'Populating Music Files: ', '[', Counter(), '/%d] ' % count],
                maxval=count)
            progress.start()

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
                self.device.push_file(music_file, 1, os.path.join(destination,
                                      remote_filename))
                progress.update(i)

            progress.finish()

    def populate_pictures(self, count, source='IMG_0001.jpg',
                          destination='sdcard/DCIM/100MZLLA'):
        self.populate_files('picture', source, count, destination)

    def populate_videos(self, count, source='VID_0001.3gp',
                        destination='sdcard/DCIM/100MZLLA'):
        self.populate_files('video', source, count, destination)

    def populate_files(self, file_type, source, count, destination=''):
        self.remove_media(file_type)
        progress = ProgressBar(
            widgets=['Populating %s Files: ' % file_type.capitalize(), '[',
                     Counter(), '/%d] ' % count], maxval=count)
        progress.start()
        self.device.push_file(
            pkg_resources.resource_filename(
                __name__, os.path.sep.join(['resources', source])),
            count,
            destination,
            progress)
        progress.finish()

    def remove_media(self, file_type):
        if self.device.is_android_build:
            files_attr = getattr(self.data_layer, '%s_files' % file_type)
            files = files_attr() or []
            if len(files) > 0:
                progress = ProgressBar(widgets=[
                    'Removing %s Files: ' % file_type.title(),
                    '[', Counter(),
                    '/%d] ' % len(files)], maxval=len(files))
                for filename in progress(files):
                    self.device.manager.removeFile(filename)
                files = files_attr() or []
            if not len(files) == 0:
                raise IncorrectCountError(
                    '%s files' % file_type, 0, len(files))

    def start_b2g(self):
        self.device.start_b2g()
        self.data_layer = GaiaData(self.marionette)


def cli():
    parser = OptionParser(usage='%prog [options]')
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
        help='number of contacts to create')
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

    data_types = ['call', 'contact', 'message', 'music', 'picture', 'video']
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
    B2GPopulate(marionette).populate(
        options.call_count,
        options.contact_count,
        options.message_count,
        options.music_count,
        options.picture_count,
        options.video_count)


if __name__ == '__main__':
    cli()
