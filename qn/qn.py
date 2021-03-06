#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import qn.hotkey_manager as hotkey_manager

from os import system, path, makedirs, walk, stat, rename, rmdir
from sys import exit
from subprocess import Popen, PIPE, call
from stat import ST_CTIME, ST_ATIME, ST_MTIME, ST_SIZE
from operator import itemgetter
import mimetypes
from datetime import datetime


# Check if program exists - linux only
def cmd_exists(cmd):

    return call("type " + cmd, shell=True, stdout=PIPE, stderr=PIPE) == 0


def file_mime_type(filename):

    mtype, menc = mimetypes.guess_type(filename)
    # If type is not detected, just open as plain text
    if not mtype:
        mtype = 'None/None'
    return(mtype)


def file_mime_type_bash(filepath):
    # This is more reliable it seems.

    if not cmd_exists('xdg-mime'):
        return(file_mime_type(filepath))
    proc = Popen(['xdg-mime', 'query', 'filetype', filepath],
                 stdout=PIPE)
    mtype = proc.stdout.read().decode('utf-8')
    proc.wait()
    if not mtype:
        mtype = 'None/None'

    return(mtype)


def terminal_open(terminal, command, title=None):
    if not title:
        title = 'qn: ' + terminal
    else:
        title = 'qn: ' + title

    if terminal in ['urxvt', 'xterm', 'gnome-terminal']:
        generated_command = terminal + ' -title "' + title + '"'
    elif terminal in ['termite', 'xfce-terminal']:
        generated_command = terminal + ' --title "' + title + '"'
    else:
        generated_command = terminal + ' -T "' + title + '"'

    system(generated_command + " -e " + command)


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


class FileRepo:
    def __init__(self, dirpath=None):
        self.__path = path.join(dirpath, "")
        self.__path_len = len(self.__path)
        self.__file_list = []    # list of files - dicts
        self.__pfile_list = []  # list of pinned files - dicts
        self.__pinned_filenames = []  # List of filenames that will be pinned
        self.__sorttype = "none"
        self.__sortrev = False

        self.__filecount = 0
        self.__pfilecount = 0

        self.__tags = None

        self.__lineformat = ['name', 'cdate']
        self.__linebs = {}
        self.__linebs['name'] = 40
        self.__linebs['adate'] = 18
        self.__linebs['cdate'] = 18
        self.__linebs['mdate'] = 18
        self.__linebs['size'] = 15
        self.__linebs['misc'] = 100
        self.__linebs['tags'] = 50

    @property
    def sorttype(self):
        return(self.__sorttype)

    @property
    def sortrev(self):
        return(self.__sortrev)

    def scan_files(self):
        """Scans the directory for files and populates the file list and
        linebs.
        """
        self.__filecount = 0
        self.__pfilecount = 0
        pintot = len(self.__pinned_filenames)
        if pintot != 0:
            temp_pinned_filenames = list(self.__pinned_filenames)
        else:
            temp_pinned_filenames = False

        for root, dirs, files in walk(self.__path, topdown=True):
            for name in files:
                fp = path.join(root, name)
                fp_rel = fp[self.__path_len:]

                if (fp_rel[0] == '.'):
                    continue
                try:
                    filestat = stat(fp)
                except:
                    continue

                file_props = {}
                file_props['size'] = filestat[ST_SIZE]
                file_props['adate'] = filestat[ST_ATIME]
                file_props['mdate'] = filestat[ST_MTIME]
                file_props['cdate'] = filestat[ST_CTIME]
                file_props['name'] = fp_rel
                file_props['fullpath'] = fp
                file_props['misc'] = None
                file_props['tags'] = None

                if temp_pinned_filenames:
                    if name in temp_pinned_filenames:
                        temp_pinned_filenames.remove(name)
                        self.__pfile_list.append(file_props)
                        self.__pfilecount += 1
                        continue

                    self.__file_list.append(file_props)
                    self.__filecount += 1
                    continue

                # if name in self.pinned_filenames:
                #     self.__pfile_list.append(file_props)
                #     self.__pfilecount += 1
                # else:
                #     self.__file_list.append(file_props)
                #     self.__filecount += 1
                self.__file_list.append(file_props)
                self.__filecount += 1

    def add_file(self, filepath, misc_prop=None):
        """Add a file to the file repo.

        Keyword arguments:
        filepath -- path to file
        misc_props -- string to add as a 'misc' property to file
        """
        if not path.isfile(filepath):
            print(filepath + " is not a file.")
            exit(1)

        fp_rel = filepath[self.__path_len:]

        try:
            filestat = stat(filepath)
        except:
            return

        file_props = {}
        file_props['size'] = filestat[ST_SIZE]
        file_props['adate'] = filestat[ST_ATIME]
        file_props['mdate'] = filestat[ST_MTIME]
        file_props['cdate'] = filestat[ST_CTIME]
        file_props['name'] = fp_rel
        file_props['fullpath'] = filepath
        file_props['misc'] = misc_prop

        self.__file_list.append(file_props)
        self.__filecount += 1

    def sort(self, sortby='name', sortrev=False):
        """Sort notes

        Keyword arguments:
            sortby -- type of sort (default 'name')
            sortrev -- boolean on whether to do a reverse sort
        """
        if sortby not in ['size', 'adate', 'mdate', 'cdate', 'name']:
            print("Key '" + sortby + "' is not valid.")
            print("Choose between size, adate, mdate, cdate or name.")

        self.__file_list = sorted(self.__file_list,
                                  key=itemgetter(sortby), reverse=not sortrev)
        self.__sorttype = sortby
        self.__sortrev = sortrev

    def get_property_list(self, prop='name', pinned_first=True):
        """Get a list of a particular property for each file."""
        if pinned_first:
            plist = list(itemgetter(prop)(filen) for filen in self.__file_list)
            plist += list(itemgetter(prop)(filen) for filen in
                          self.__pfile_list)
        else:
            plist = list(itemgetter(prop)(filen) for filen in
                         self.__pfile_list)
            plist += list(itemgetter(prop)(filen) for filen in
                          self.__file_list)
        return(plist)

    def is_empty(self):
        return(not self.__filecount > 0)

    def filenames(self, pinned_first=True):
        """Get a list of filenames"""
        return(self.get_property_list('name', pinned_first))

    def filepaths(self, pinned_first=True):
        """Get a list of filepaths"""
        return(self.get_property_list('fullpath', pinned_first))

    def filecount(self, include_normal=True, include_pinned=True):
        """Get the number of files in the repo"""
        return(self.__filecount + self.__pfilecount)

    def set_lineformat(self, new_lineformat):
        """Set the lineformat, which is a list of properties in the order
        in which they should be arranged by lines().
        """
        self.__lineformat = new_lineformat

    def lines(self, format_list=None, pinned_first=True):
        """Return a list of nicely formattted lines for each file."""
        lines = []
        if not format_list:
            format_list = self.__lineformat
        for filen in self.__file_list:
            line = ""
            for formatn in format_list:
                if formatn in ['adate', 'mdate', 'cdate']:
                    block = datetime.utcfromtimestamp(filen[formatn])
                    block = block.strftime('%d/%m/%Y %H:%M')
                elif formatn == 'size':
                    size = filen[formatn]
                    block = sizeof_fmt(size)
                else:
                    block = str(filen[formatn])

                blocksize = self.__linebs[formatn]
                if len(block) >= blocksize:
                    block = block[:blocksize-2] + '…'

                block = block.ljust(blocksize)
                line += block

            lines.append(line)

        return(lines)

    def pin_files(self, filelist_topin):
        """Pin a file WIP"""
        self.__pinned_filenames = filelist_topin
        return(1)

    def search_files(self, queries_list):
        """Search the contents of files and return matches."""
        if not self.__file_list:
            print("No files added to file repo")
            return(1)
        results_file_repo = FileRepo(self.__path)
        for fp in self.filepaths():
            match = ""
            queries_p = list(queries_list)
            notefile = open(fp, 'r')
            try:
                for line in notefile:
                    if not queries_p:
                        results_file_repo.add_file(fp, match)
                        notefile.close()
                        break
                    for qp in list(queries_p):
                        if qp.lower() in line.lower():
                            match = line
                            queries_p.remove(qp)
            except:  # Not pretty, but for now it works.
                continue
        print(results_file_repo.filecount(), results_file_repo.is_empty())
        if results_file_repo.is_empty():
            return(None)
        else:
            return(results_file_repo)

    def grep_files(self, filters_string):
        """Search the contents of files and return matches. Uses grep."""
        if not self.__file_list:
            print("No files added to file repo")
            return(1)
        grep_file_repo = FileRepo(self.__path)

        proc = Popen(['grep', '-i', '-I', filters_string] + self.filepaths(),
                     stdout=PIPE)
        answer = proc.stdout.read().decode('utf-8')
        proc.wait()

        grep_file_repo = FileRepo(self.__path)
        temp_files = []
        if answer == '':
            return(None)

        for ans in answer.split("\n"):
            if ans:
                ans = ans.split(':', 1)
                if not ans[0] in temp_files:
                    grep_file_repo.add_file(ans[0], ans[1])
                    temp_files.append(ans[0])

        return(grep_file_repo)


class QnApp ():
    """Class that handles notes.

    Keyword arguments:
    qnoptions -- QnOptions class.
    """
    def __init__(self, qnoptions):
        self.__options = qnoptions
        self.__app = qnoptions.app
        self.__qndir = qnoptions.qndir
        self.__qntrash = qnoptions.qntrash
        self.__hkman = {}
        self.__file_repo = {}

    def add_repo(self, repopath=None, repoinstance='default',):
        """Add a note repository to an instance of qn. It creates a FileRepo
        class.

        Keyword arguments:
        repopath -- path from which to generate the note repository. If None,
                    use the one in self.options (default None)
        repoinstance -- qn instance name for the repository. This allows qn
                        to have multiple repositories that can be handled
                        independently.
        """
        if repopath is None:
            repopath = self.__qndir
        self.__file_repo[repoinstance] = FileRepo(repopath)

    def add_existing_repo(self, existing_file_repo, repoinstance):
        """Add an existing, populated, FileRepo class to an instance."""
        self.__file_repo[repoinstance] = existing_file_repo

    @property
    def app(self):
        return(self.__app)

    @property
    def launcher(self):
        return(self.__app)

    @property
    def options(self):
        return(self.__options)

    @property
    def qndir(self):
        return(self.__qndir)

    @property
    def qntrash(self):
        return(self.__qntrash)

    def hkman(self, instance='default'):
        if instance in self.__hkman.keys():
            return(self.__hkman[instance])
        else:
            return(False)

    def add_hkman(self, instance='default'):
        """Add HotkeyManager class to a qn instance"""
        self.__hkman[instance] = hotkey_manager.HotkeyManager(app=self.__app)

    def file_repo(self, instance='default'):
        if instance in self.__file_repo.keys():
            return(self.__file_repo[instance])
        else:
            return(False)
            # print("Error: File repository '" + instance + "' does not exist."
            #         + " Please add it using add_repo().")
            # exit(1)

    def list_notes(self, printby='filenames', instance='default',
                   lines_format_list=None, pinned_first=True):
        """Print a list of notes.

        Keyword arguments:
        printby -- string that identifies property of notes to print
                   (default filenames)
        instance -- qn instance to print (default 'default')
        lines_format_list -- list of format names used in printby='lines'
                             (default None)
        pinned_first -- Not Implemented
        """
        if not self.__file_repo:
            print("Please populate QnApp with a file repository.")
            print("This can be done via QnApp.add_repo()")
            exit(1)
        if printby == 'filenames':
            for filename in self.__file_repo[instance].filenames(pinned_first):
                print(filename)
        elif printby == 'filepaths':
            for filename in self.__file_repo[instance].filepaths(pinned_first):
                print(filename)
        elif printby == 'lines':
            lines = self.__file_repo[instance].lines(lines_format_list,
                                                     pinned_first)
            for line in lines:
                print(line)

        else:
            print("Error: '" + printby + "' is not a valid printby setting." +
                  " Use 'filenames', 'filepaths', or 'lines'.")

    def find_note(self, findstringlist, open_note=False, instance='default'):
        """Find a note based on a list of strings.

        Keyword Arguments:
            findstringlist -- list of strings to match with note names.
            open_note -- boolean on whether to open the note found
            instance -- qn instance on which to conduct the matching"""

        tmp_filelist = self.__file_repo[instance].filenames()[:]
        found_list = []
        for filen in tmp_filelist:
            if all((fstring in filen) for fstring in findstringlist):
                if open_note:
                    found_list.append(filen)
                else:
                    print(filen)

        if open_note:
            found_num = len(found_list)
            if found_num > 1:
                print("Many notes found, select which to open:")
                ct = 0
                for filen in found_list:
                    print('  (' + str(ct) + ') ' + filen)
                    ct += 1
                selection = input('Select between 0-' + str(found_num-1) +
                                  '> ')
                try:
                    seln = int(selection)
                except (ValueError):
                    print('Invalid selection "' + selection + '".')
                    exit(1)
                if seln not in range(found_num):
                    print('Invalid selection "' + selection + '".')
                    exit(1)
                else:
                    print("Opening " + found_list[seln] + "...")
                    self.open_note(found_list[seln])
            elif found_num == 1:
                print("Opening " + found_list[0] + "...")
                self.open_note(found_list[0])
            else:
                print('No notes found.')
                if len(findstringlist) > 1:
                    print("Search terms were: ")
                    for fstring in findstringlist[0]:
                        print(fstring)
                else:
                    print("Opening " + findstringlist[0][0] + "...")
                    self.new_note(findstringlist[0][0])
        return(found_list)

    def move_note(self, name1, name2, dest1=None, dest2=None, move_tags=False):
        """Move a note.

        Keyword arguments:
        name1 -- name of note to rename
        name2 -- target name
        dest1 -- path of original note
        dest2 -- target path
        move_tags -- move tags (not implemented)
        """
        if dest1 is None:
            dest1 = self.qndir

        if not dest2:
            dest2 = self.qndir

        has_sp1 = False
        has_sp2 = False

        if ('/' in name1):
            has_sp1 = True
            sd1, sn1 = name1.rsplit('/', 1)
            td1 = path.join(dest1, sd1)
        else:
            sn1 = name1
            td1 = dest1

        if ('/' in name2):
            has_sp2 = True
            sd2, sn2 = name2.rsplit('/', 1)
            td2 = path.join(dest2, sd2)
        else:
            sn2 = name2
            td2 = dest2

        full_dir1 = path.join(td1, sn1)
        full_dir2 = path.join(td2, sn2)
        if (full_dir1 == full_dir2):
            print('Source and destination are the same. Doing nothing.')
            exit(0)

        # check if destination already exists
        if path.exists(full_dir2):
            print('Note with same name found, creating conflict.')
            appended = "-conflict-"
            appended += datetime.now().strftime('%Y%m%d_%H%M%S')
            full_dir2 += appended
            name2 += appended

        if has_sp2:
            if not (path.isdir(td2)):
                print('creating ' + td2)
                makedirs(td2)
        # move the file
        try:
            rename(full_dir1, full_dir2)
            # if move_tags:
            #     tagsdict = load_tags()
            #     if name1 in tagsdict:
            #         tagsdict[name2] = tagsdict[name1]
            #         tagsdict.pop(name1)
            #         save_tags(tagsdict)
            print('Moved ' + full_dir1 + ' to ' + full_dir2)
        except OSError:
            exit(1)

        if has_sp1:
            try:
                rmdir(td1)
                print('deleted ' + td1)
            except OSError:
                print('not deleted ' + td1)
                exit(0)

        exit(0)

    def delete_note(self, note):
        """Delete a note by moving it to the trash."""

        self.move_note(note, note, dest1=self.qndir, dest2=self.qntrash)

    def undelete_note(self, note):
        """Undelete note by moving it from the trash"""

        self.move_note(note, note, dest1=self.qntrash, dest2=self.qndir)

    def open_note(self, note):
        """Open a note."""

        inter = self.options.interactive
        fulldir = path.join(self.qndir, note)
        if path.isfile(fulldir):
            # mime = file_mime_type(note).split("/")
            mime = file_mime_type_bash(fulldir).strip().split("/")
            fulldir = path.join(self.qndir, note).strip()
            editor_command = self.options.editor + " '" + fulldir + "'"

            if (mime[0] == 'text' or mime[0] == 'None'):
                if inter:
                    system(editor_command)
                else:
                    terminal_open(self.options.terminal, editor_command)
                    # os.system(self.options.terminal + " -e "
                    #          + self.options.editor + " " + fulldir)
            elif (mime[1] == 'x-empty'):
                if inter:
                    system(editor_command)
                else:
                    terminal_open(self.options.terminal, editor_command)
                    # system(self.options.terminal + " -e "
                    #           + self.options.editor + " " + fulldir)
            else:
                system(self.options.opener + " " + fulldir)
        else:
            print(fulldir + " is not a note")
            exit(1)

    def new_note(self, note):
        """Create a new note"""

        inter = self.options.interactive
        if '/' in note:
            note_dir = note.rsplit('/', 1)[0]
            if not path.isdir(note_dir):
                makedirs(path.join(self.qndir, note_dir), exist_ok=True)
        editor_command = self.options.editor + " '"
        editor_command += path.join(self.qndir, note).strip()
        editor_command += "'"
        if inter:
            system(self.options.editor + " " +
                   path.join(self.qndir, note))
        else:
            terminal_open(self.options.terminal, editor_command, note)
            # system(self.options.terminal + ' -e ' + self.options.editor
            #           + " " + path.join(self.__qndir, note))
        return(0)

    def force_new_note(self, note):
        """Force create a new note"""
        filepath = path.join(self.qndir, note.strip())
        if path.isfile(filepath):
            self.open_note(note)

        else:
            self.new_note(note)
        return(0)

# # FOR TAG SUPPORT
# def load_tags():
#     tagfile = open(_TAGF_PATH, 'rb')
#     tagdict = pickle.load(tagfile)
#     tagfile.close()
#
#     return(tagdict)
#
#
# def save_tags(newdict):
#
#
#     tagfile = open(_TAGF_PATH, 'wb')
#     pickle.dump(newdict, tagfile)
#     tagfile.close()
#
#
# def list_tags():
#
#
#     tagslist = load_tags()['__taglist']
#     return(tagslist)
#
#
# def create_tag(tagname):
#
#
#     tagsdict = load_tags()
#     if not tagname in tagsdict['__taglist']:
#         tagsdict['__taglist'].append(tagname)
#         save_tags(tagsdict)
#
#     return(tagsdict)
#
#
# def add_note_tag(tagname, notename, tagsdict=None):
#
#
#     if not os.path.isfile(os.path.join(QNDIR, notename)):
#         print('Note does not exist. No tag added.')
#         exit(0)
#     tagsdict = create_tag(tagname)
#     if notename in tagsdict:
#         if tagname in tagsdict[notename]:
#             print('Note already has tag. Doing nothing')
#         else:
#             tagsdict[notename].append(tagname)
#             save_tags(tagsdict)
#     else:
#         tagsdict[notename] = [tagname]
#         save_tags(tagsdict)
#
#     return(tagsdict)
#
#
# def del_note_tag(tagname, notename, tagsdict=None):
#
#
#     if not os.path.isfile(os.path.join(QNDIR, notename)):
#         print('Note does not exist. No tag removed.')
#         exit(0)
#
#     if not tagsdict:
#         tagsdict = load_tags()
#
#     if notename in tagsdict:
#         if tagname in tagsdict[notename]:
#             tagsdict[notename].remove(tagname)
#             if not list_notes_with_tags(tagname, tagsdict):
#                 tagsdict['__taglist'].remove(tagname)
#             save_tags(tagsdict)
#     else:
#         pass
#
#     return(tagsdict)
#
#
# def clear_note_tags(notename, tagsdict=None):
#
#
#     if not os.path.isfile(os.path.join(QNDIR, notename)):
#         print('Note does not exist. Doing nothing.')
#         exit(0)
#     if not tagsdict:
#         tagsdict = load_tags()
#     tagsdict.pop(notename, None)
#
#     return(tagsdict)
#
#
# def list_note_tags(notename):
#
#
#     if not os.path.isfile(os.path.join(QNDIR, notename)):
#         print('Note does not exist.')
#         exit(0)
#
#     tagsdict = load_tags()
#     if notename in tagsdict:
#         return(tagsdict[notename])
#     else:
#         return([])
#
#
# def list_notes_with_tags(tagname, tagsdict=None):
#
#
#     if not tagsdict:
#         tagsdict = load_tags()
#
#     filtered_list = []
#     for key,value in tagsdict.items():
#        if key == '__taglist':
#             continue
#         if tagname in value:
#             filtered_list.append(key)
#
#     return(filtered_list)


# if __name__ == '__main__':
    # Create an options class that reads the config file and checks
    # the environment.
    # qn_options = config_parse.QnOptions(run_parse_config=True)
    # qn_options.check_environment()

    # Create a QnApp configured with the QnOptions class above.
    # Populate this QnApp with a File_Repo class
    # qn = QnApp(qn_options)
    # qn.add_repo()
    # pass

    # Pin certain files in the file repo. Pin files before scanning the
    # directory.
    # qn.file_repo().pin_files(['pinplease', 'nothing'])

    # # Scan the directory of the file repository and sort it
    # qn.file_repo().scan_files()
    # qn.file_repo().sort('size', True)
    # print(qn.options().print_options())

#    qn.list_notes()
#    grep = qn.file_repo().grep_files('world')

#    tfile=grep.filenames()[0]
    # qn.open_note('test')

    # qn.list_files('filepaths')
    # qn.list_files('lines', lines_format_list=['name', 'size', 'cdate'])

    # # Print the first ten entries with a header
    # n = 0
    # print("File List (" + str(qn.file_repo().filecount()) + ")")
    # print("---------")
    # for filen in qn.file_repo().filenames():
    #     print(filen)
    #     if n == 10:
    #         print("...\n")
    #         break
    #     n += 1

    # # Print the elapsed time since libraries were loaded
    # timeb = time.time()
    # print('Elapsed time: ' + str(timeb-timea) + ' seconds')

#     parser = argparse.ArgumentParser(prog='qn',
#                         description="Quick Note Manager.")
#     parser.add_argument('-l', '--list-notes', action='store_true'
#                         , default=False
#                 , help='list notes in note directory')
#     parser.add_argument('-s', '--search', nargs='*', default=-1
#                 , help='search for note')
#     parser.add_argument('-o', '--open-note', action='store_true'
#                         , default=False
#                         , help='open')
#
#     args = parser.parse_args()
#     #print(args)
#
#     check_environment()
#     filerepo = FileRepo(QNDIR)
#     filerepo.scan_files()
#     if args.list_notes:
#         for filen in filerepo.filenames():
#             print(filen)
#         exit(0)
#     if args.search != -1:
#         search_list = filerepo.filenames()
#         for filen in filerepo.filenames():
#             bool_list = []
#             for search_string in args.search:
#                 bool_list.append(search_string in filen)
#             if all(bool_list):
#                 print(filen)
#
#         exit(0)
