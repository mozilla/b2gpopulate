#!/usr/bin/env python
#
# Before running this:
# 1) Install a B2G build with Marionette enabled
# 2) adb forward tcp:2828 tcp:2828

from optparse import OptionParser
import os
import pkg_resources
from zipfile import ZipFile

from progressbar import Counter
from progressbar import ProgressBar

from marionette import Marionette
from gaiatest import GaiaData
from gaiatest import GaiaDevice


class CountError(Exception):
    """Exception for a count being incorrect"""
    def __init__(self, type, expected, actual):
        Exception.__init__(
            self, 'Incorrect number of %s. Expected %s but found %s' % (type, expected, actual))


class B2GPopulate:

    def __init__(self, marionette):
        self.marionette = marionette
        self.data_layer = GaiaData(self.marionette)
        self.device = GaiaDevice(self.marionette)

    def populate(self, contact_count=0, message_count=0, music_count=0,
                 picture_count=0, video_count=0):

        if self.device.is_android_build:
            media_files = self.data_layer.media_files or []
            if len(media_files) > 0:
                progress = ProgressBar(widgets=[
                    'Removing Media: ',
                    '[', Counter(),
                    '/%d] ' % len(media_files)], maxval=len(media_files))
                for filename in progress(media_files):
                    self.device.manager.removeFile(filename)
                media_files = self.data_layer.media_files
            if not len(media_files) == 0:
                raise CountError('media files', 0, len(media_files))

        if contact_count:
            self.populate_contacts(contact_count)

        if message_count:
            self.populate_messages(message_count)

        if music_count > 0:
            self.populate_music(music_count)

        if picture_count > 0:
            self.populate_files('pictures', 'IMG_0001.jpg', picture_count, 'sdcard/DCIM/100MZLLA')

        if video_count > 0:
            self.populate_files('videos', 'VID_0001.3gp', video_count, 'sdcard/DCIM/100MZLLA')

    def populate_contacts(self, count):
        progress = ProgressBar(widgets=[
            'Contacts: ', '[', Counter(), '/%d] ' % count], maxval=count)
        progress.start()
        for marker in [2000, 1000, 500, 200, 0]:
            if count >= marker:
                db_zip = ZipFile(pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'contactsDb.zip'])))
                db = db_zip.extract('contactsDb-%d.sqlite' % marker)
                self.device.stop_b2g()
                self.device.push_file(
                    db, destination='data/local/indexedDB/chrome/3406066227csotncta.sqlite')
                os.remove(db)
                self.device.start_b2g()
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
            raise Exception('Invalid value for message count, use one of: %s' %
                            ', '.join([str(count) for count in db_message_counts]))
        progress = ProgressBar(widgets=[
            'Messages: ', '[', Counter(), '/%d] ' % count], maxval=count)
        progress.start()
        db_message_counts.sort(reverse=True)
        for marker in db_message_counts:
            if count >= marker:
                db_zip = ZipFile(pkg_resources.resource_filename(
                    __name__, os.path.sep.join(['resources', 'smsDb.zip'])))
                db = db_zip.extract('smsDb-%d.sqlite' % marker)
                self.device.stop_b2g()
                self.device.push_file(
                    db, destination='data/local/indexedDB/chrome/226660312ssm.sqlite')
                os.remove(db)
                self.device.start_b2g()
                progress.update(marker)
                progress.finish()
                break

    def populate_music(self, count, source='MUS_0001.mp3', destination='sdcard'):
        import math
        import tempfile
        from mutagen.easyid3 import EasyID3
        music_file = pkg_resources.resource_filename(
            __name__, os.path.sep.join(['resources', source]))
        local_filename = music_file.rpartition(os.path.sep)[-1]

        # copy the mp3 file into a temp location
        with tempfile.NamedTemporaryFile() as local_copy:
            local_copy.write(open(music_file).read())
            music_file = local_copy.name

            mp3 = EasyID3(music_file)

            tracks_per_album = 10

            progress = ProgressBar(widgets=['Music: ', '[', Counter(), '/%d] ' % count], maxval=count)
            progress.start()

            for i in range(1, count + 1):
                album = math.ceil(float(i) / float(tracks_per_album))
                track = i - ((album - 1) * tracks_per_album)
                mp3['title'] = 'Track %d' % track
                mp3['artist'] = 'Artist %d' % album
                mp3['album'] = 'Album %d' % album
                mp3['tracknumber'] = str(track)
                mp3.save()
                remote_filename = '_%s.'.join(iter(local_filename.split('.'))) % i
                self.device.push_file(music_file, 1, os.path.join(destination, remote_filename))
                progress.update(i)

            progress.finish()

    def populate_files(self, file_type, source, count, destination=''):
        progress = ProgressBar(
            widgets=['%s: ' % file_type.capitalize(), '[', Counter(), '/%d] ' % count],
            maxval=count)
        progress.start()
        self.device.push_file(
            pkg_resources.resource_filename(__name__, os.path.sep.join(['resources', source])),
            count,
            destination,
            progress)
        progress.finish()


def cli():
    parser = OptionParser(usage='%prog [options]')
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
        help='number of messages to create. must be one of: 0, 200, 500, 1000, 2000')
    parser.add_option(
        '--music',
        action='store',
        type=int,
        dest='music_count',
        default=0,
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

    data_types = ['contact', 'message', 'music', 'picture', 'video']
    for data_type in data_types:
        count = getattr(options, '%s_count' % data_type)
        if count and not count >= 0:
            parser.print_usage()
            print 'invalid value for %s count!' % data_type
            parser.exit()

    counts = [getattr(options, '%s_count' % data_type) for data_type in data_types]
    if not any([count for count in counts if count > 0]):
        parser.print_usage()
        print 'must specify at least one item to populate'
        parser.exit()

    # only allow preset db values for messages
    db_message_counts = [0, 200, 500, 1000, 2000]
    if options.message_count and not options.message_count in db_message_counts:
        parser.print_usage()
        print 'invalid value for message count, use one of: %s' % \
              ', '.join([str(count) for count in db_message_counts])
        parser.exit()

    # TODO command line option for address
    marionette = Marionette(host='localhost', port=2828, timeout=180000)
    marionette.start_session()
    B2GPopulate(marionette).populate(
        options.contact_count,
        options.message_count,
        options.music_count,
        options.picture_count,
        options.video_count)


if __name__ == '__main__':
    cli()
