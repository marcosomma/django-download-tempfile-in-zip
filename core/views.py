import os
import zipfile
import tempfile
import StringIO

from django.http import HttpResponse


def getfiles(request):
	f = tempfile.NamedTemporaryFile(mode='w+b', prefix='base', suffix='.txt', delete=False)
	f.write("Hello World!\n")
	f.close()

	g = tempfile.NamedTemporaryFile(mode='w+b', prefix='editor', suffix='.xml', delete=False)
	g.write("<provaXML>Hello World22222222!</provaXML>\n")
	g.close()
	
	files = [f.name ,g.name]

	zip_filename = "course.zip"

	s = StringIO.StringIO()

	zf = zipfile.ZipFile(s, "a") # "a" utiliza files / "w" escribe los files

	for fpath in files:
	 	fname = os.path.split(fpath)
		zip_path = os.path.join(fname[1])
		zf.write(fpath, zip_path)

	zf.close()

	resp = HttpResponse(s.getvalue(), mimetype = "application/x-zip-compressed")
	resp['Content-Disposition'] = 'attachment; filename=%s' % zip_filename

	return resp