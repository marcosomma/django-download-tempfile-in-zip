import zipfile, os, re, fnmatch, subprocess, tempfile, settings, shutil
from django.db.models import Q
from itertools import islice, chain

from django.core import serializers

human_size = lambda s:[(s%1024**i and "%.1f"%(s/1024.0**i) or str(s/1024**i))+x.strip() for i,x in enumerate(' KMGTPEZY') if s<1024**(i+1) or i==8][0]

keep_in_repo_after_install = getattr(settings, 'KEEP_IN_REPOSITORY_AFTER_INSTALL', True)

def find_program_path(program):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def getLength(filename, inseconds=True):
    '''get video legth'''
    extension_to_get_length = ('wmv', 'flv', 'avi', 'mov', 'mpg', 'mp4', 'vob', 'webm', 'mp3')
    if os.path.isfile(filename) and filename.split(".")[-1].lower() in extension_to_get_length:
        result = subprocess.Popen(["ffmpeg", '-i', filename],
        stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        duration = [x for x in result.stdout.readlines() if "Duration" in x]
        print "duration", duration
        d = duration[0].strip().split()[1]
        if inseconds:
            d = d.replace(".", ":").replace(",","").split(":")
            d = int(d[1])*60+int(d[2])
            return d
        else:
            return d

def normalize_query(query_string,
                    findterms=re.compile(r'"([^"]+)"|(\S+)').findall,
                    normspace=re.compile(r'\s{2,}').sub):
    ''' Splits the query string in invidual keywords, getting rid of unecessary spaces
        and grouping quoted words together.
        Example:

        >>> normalize_query('  some random  words "with   quotes  " and   spaces')
        ['some', 'random', 'words', 'with quotes', 'and', 'spaces']
    '''
    query_string = query_string.replace("'", '"')
    return [normspace(' ', (t[0] or t[1]).strip()) for t in findterms(query_string)] 

def get_query(query_string, search_fields):
    ''' Returns a query, that is a combination of Q objects. That combination
        aims to search keywords within a model by testing the given search fields.
    '''
    query = None # Query to search for every search term        
    terms = normalize_query(query_string)
    for term in terms:
        or_query = None # Query to search for a given term in each field
        for field_name in search_fields:
            q = Q(**{"%s__icontains" % field_name: term})
            if or_query is None:
                or_query = q
            else:
                or_query = or_query | q
        if query is None:
            query = or_query
        else:
            query = query | or_query
    return query
    
def zipdir(dir, zip_file):
    print "Zipping %s into %s" % (dir, zip_file)
    zip = zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED)
    root_len = len(os.path.abspath(dir))
    for root, dirs, files in os.walk(dir):
        archive_root = os.path.abspath(root)[root_len:]
        for f in files:
            fullpath = os.path.join(root, f)
            archive_name = os.path.join(archive_root, f)
            print f
            zip.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)
    zip.close()
    return zip_file
    

def folder_size(folder,inbytes=True):
    folder_size = 0
    for (path, dirs, files) in os.walk(folder):
      for file in files:
        filename = os.path.join(path, file)
        folder_size += os.path.getsize(filename)
    if inbytes:
        return folder_size
    else:
        return "%0.1f MB" % (folder_size/(1024*1024.0))

def locate(pattern, root=os.curdir):
    '''Locate all files matching supplied filename pattern in and below
    supplied root directory.
    from: http://code.activestate.com/recipes/499305-locating-files-throughout-a-directory-tree/
    '''
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)

def ImportItem(filepath, folder=settings.CONTENT_ROOT, delete_after=True, force=False):
    try:
        tmpfolder = tempfile.mkdtemp()
        #unzip
        unzipcommand = "unzip -o %s -d %s" % (filepath, tmpfolder)
        subprocess.call(unzipcommand, shell=True)
        # read json
        descriptor = "%s/descriptor.xml" % tmpfolder
        if os.path.isfile(descriptor):
            fl = open(descriptor)
            data = fl.read()
            #try:
            deserialized = serializers.deserialize("xml", data)
            a = []
            for r in deserialized: #its only one, but we need this
                r.object.pageviews = 0
                r.save()
                a.append(r)
            # content on db, copying
            dest = os.path.dirname(a[0].object.content_root())
            if not os.path.isdir(dest):
                try:
                    # trying to create
                    os.makedirs(dest)
                except OSError, err:
                    print "Dir exists or have no permission!"
                    # remove tmp
                    shutil.rmtree(tmpfolder)
                    raise
                    return False
            # copy from tmpfolder to dest
            copycommand = "cp -rvf %s/* %s" % (tmpfolder, dest)
            subprocess.call(copycommand, shell=True)
            # remove tmp
            shutil.rmtree(tmpfolder)
            if keep_after_install:
                # keep/copy item into repository
                repo_path = os.path.dirname(a[0].object.repository_root())
                if not os.path.exists(repo_path):
                    subprocess.call("mkdir -vp %s" % repo_path, shell=True)
                cpcmd = "cp -rvf %s %s" % (filepath, repo_path)
                subprocess.call(cpcmd, shell=True)
            # remove installed file from installfolder ;)
            rmcommand = u"rm -v %s" % filepath
            subprocess.call(rmcommand, shell=True)
        return True
    except:
        raise
        return False

## labs ##
##
##  LABS LABS LABS
##