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


class B2GPopulate:

    def __init__(self, marionette):
        self.marionette = marionette
        self.data_layer = GaiaData(self.marionette)
        self.device = GaiaDevice(self.marionette)

    def populate(self, contact_count=0, message_count=0, music_count=0,
                 picture_count=0, video_count=0):

        if self.device.is_android_build and self.data_layer.media_files:
            for filename in self.data_layer.media_files:
                self.device.manager.removeFile('/'.join(['sdcard', filename]))

        if contact_count:
            self.populate_contacts(contact_count)

        if message_count:
            self.populate_messages(message_count)

        if music_count > 0:
            self.populate_files('music', 'MUS_0001.mp3', music_count, 'sdcard')

        if picture_count > 0:
            self.populate_files('pictures', 'IMG_0001.jpg', picture_count, 'sdcard/DCIM/100MZLLA')

        if video_count > 0:
            self.populate_files('videos', 'VID_0001.3gp', video_count, 'sdcard/DCIM/100MZLLA')

    def populate_contacts(self, count):
        progress = ProgressBar(widgets=['Contacts: ', '[', Counter(), '/%d] ' % count], maxval=count)
        progress.start()
        for marker in [2000, 1000, 500, 200, 0]:
            if count >= marker:
                db_zip = ZipFile(pkg_resources.resource_filename(__name__, os.path.sep.join(['resources', 'contactsDb.zip'])))
                db = db_zip.extract('contactsDb-%d.sqlite' % marker)
                self.device.stop_b2g()
                self.device.push_file(db, destination='data/local/indexedDB/chrome/3406066227csotncta.sqlite')
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
            raise Exception('Invalid value for message count, use one of: %s' % ', '.join([str(count) for count in db_message_counts]))
        progress = ProgressBar(widgets=['Messages: ', '[', Counter(), '/%d] ' % count], maxval=count)
        progress.start()
        db_message_counts.sort(reverse=True)
        for marker in db_message_counts:
            if count >= marker:
                db_zip = ZipFile(pkg_resources.resource_filename(__name__, os.path.sep.join(['resources', 'smsDb.zip'])))
                db = db_zip.extract('smsDb-%d.sqlite' % marker)
                self.device.stop_b2g()
                self.device.push_file(db, destination='data/local/indexedDB/chrome/226660312ssm.sqlite')
                os.remove(db)
                self.device.start_b2g()
                progress.update(marker)
                progress.finish()
                break

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
        help='number of messages to create')
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
        print 'invalid value for message count, use one of: %s' % ', '.join([str(count) for count in db_message_counts])
        parser.exit()

    marionette = Marionette(host='localhost', port=2828)  # TODO command line option for address
    marionette.start_session()
    B2GPopulate(marionette).populate(
        options.contact_count,
        options.message_count,
        options.music_count,
        options.picture_count,
        options.video_count)


if __name__ == '__main__':
    cli()
