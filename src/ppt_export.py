import glob
import shutil
import commands
import os

try:
    import comtypes.client
except:
    pass


class ConverterError(Exception):
    """all exceptions related to the conversion """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

    
class Converter():
    """convert ppt or odp presentation to jpg images"""
    def __init__(self, path_to_presentation, target_folder):
        self.path_to_presentation = path_to_presentation
        self.target_folder = target_folder

    def convert(self):
        """will be implemented in the sublass"""
        pass


class Converter_MS(Converter):
    """converter using MS office"""
    def __init__(self, path_to_presentation, target_folder):
        Converter.__init__(self, path_to_presentation, target_folder)
        
    def convert(self):
        """use comtypes to communicate with MSoffice"""
        try:
            powerpoint = comtypes.client.CreateObject("Powerpoint.Application")
        except: # todo: exact exception
            raise ConverterError("Cannot start powerpoint")
        powerpoint.Visible = True # doesnt work otherwise !?
        try:
            powerpoint.Presentations.Open(self.path_to_presentation)
        except:
            raise ConverterError("Cannot open presentation")
        powerpoint.ActivePresentation.Export(self.target_folder, "JPG")
        self.renumber(self.target_folder)
        powerpoint.Presentations[1].Close()
        powerpoint.Quit()
        self.renumber(self.target_folder)

    def renumber(self, folder):
        """Renumber the jpg files in the folder
        so that the numbered files are sorted correctly
        """
        infiles = glob.glob(os.path.join(folder, '*.jpg'))
        print 'files are', infiles
        for filename in infiles:
            number_prefix = os.path.splitext(os.path.basename(filename))[0]
            try:
                newfilename = os.path.join(os.path.dirname(filename),
                                       '%.4d.jpg' %(int(number_prefix)))
                shutil.move(filename, newfilename)
            except ValueError:
                pass


class Converter_OO(Converter):
    """converter using Openoffice on linux"""
    def __init__(self, path_to_presentation, target_folder):
        Converter.__init__(self, path_to_presentation, target_folder)

    def convert(self):
        """use unoconv to convert """
        # copy presentation to dir
        shutil.copy(self.path_to_presentation,self.target_folder)
        tmp_presentation = os.path.join(self.target_folder,
                                  os.path.split(self.path_to_presentation)[1])
        # convert to pdf
        cmd = "unoconv -f pdf '%s'" %(tmp_presentation)
        st, output = commands.getstatusoutput(cmd)
        print 'status', st, output
        if st != 0:
            raise ConverterError("pdf conversion failed")

        pdf_presentation = os.path.splitext(tmp_presentation)[0] + '.pdf'
        if not os.path.exists(pdf_presentation):
            raise ConverterError("pdf conversion failed")
        # use ghostscript to convert pdf to images
        outfile = os.path.join(self.target_folder, "%03d.jpg")
        cmd = "gs -dBATCH -dNOPAUSE -r150 -sDEVICE=jpeg " +\
              "-sOUTPUTFILE=" + outfile + " '" +  pdf_presentation + "'"
        st, output = commands.getstatusoutput(cmd)
        # delete presentation
        os.remove(tmp_presentation)
        os.remove(pdf_presentation)


def test():
    testfolder = '/data/tmp/test'
    converter = Converter_MS('dummy', 'dummy')
    converter.renumber(testfolder)


if __name__ == '__main__':
    test()
