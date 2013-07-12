#!/usr/bin/env python

from __future__ import division
import sys, os, copy
import shutil
import glob

try:
    import cPickle as pickle
except ImportError:
    import pickle

import Image
import wx
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import tempfile

from customrubberband import RubberBand
from geticons import getBitmap
from playlist_select import PlayListSelector
from config_manager import PreferenceDialog, Config
from ppt_export import Converter_MS, Converter_OO, ConverterError
from fullscreen_help_dialog import help_dialog
## Import Image plugins separately and then convince Image that is
## fully initialized - needed when compiling for windows, otherwise
## I am not able to open tiff files with the windows binaries
import PngImagePlugin
import BmpImagePlugin
import TiffImagePlugin
import GifImagePlugin
import JpegImagePlugin
Image._initialized = 2

## ------------------------------------------
_title          = "EP viewer"
_about          = """
Eepee v 0.9.9
An application to view, analyze and present EP tracings\n
Author: Raja S. 
rajajs@gmail.com
License: GPL\n
For more information, help and for updates visit
http:\\code.google.com\p\eepee\n"""
_version = "0.9.9"
_author = "Raja Selvaraj"

#------------------------------------------------------------------------------
# Global variables
ID_OPEN        = wx.NewId()    ;   ID_UNSPLIT    = wx.NewId()
ID_SAVE        = wx.NewId()    ;   ID_CALIPER    = wx.NewId()
ID_QUIT        = wx.NewId()    ;   ID_CROP       = wx.NewId()  
ID_ROTATERIGHT = wx.NewId()    ;   ID_ROTATELEFT = wx.NewId()
ID_CALIBRATE   = wx.NewId()    ;   ID_DOODLE     = wx.NewId()
ID_PREVIOUS    = wx.NewId()    ;   ID_NEXT       = wx.NewId()
ID_CLEAR       = wx.NewId()    ;   ID_ABOUT      = wx.NewId()
ID_NEWPL       = wx.NewId()    ;   ID_EDITPL     = wx.NewId()
ID_KEYS        = wx.NewId()    ;   ID_PREF       = wx.NewId()
ID_CALIPERREMOVE = wx.NewId()  ;   ID_IMPORT     = wx.NewId()
ID_FULLSCREEN = wx.NewId()


shortcuts = """
Keyboard and mouse shortcuts:
=============================

Ctrl-o  - Open file\n
Ctrl-s  - Save file\n
Ctrl-r  - Rotate right\n
Ctrl-l  - Rotate left\n
Ctrl-b  - Calibrate\n
Ctrl-c  - Start caliper\n
Ctrl-d  - Start/stop doodle\n
Ctrl-x  - Clear doodle\n
PgDn    - Next image\n
PgDn    - Prev image\n
Ctrl-q  - Quit\n\n
Left click - Start new caliper\n
Right click - Removes caliper\n
"""

#last png is for default save ext
accepted_formats = ['.png', '.tiff', '.jpg', '.bmp', '.png'] 
accepted_wildcards = 'PNG|*.png|TIF|*.tif;*.tiff|' +\
                     'JPG|*.jpg;*.jpeg|BMP|*.bmp|' +\
                     'All files|*.*'
image_handlers = [wx.BITMAP_TYPE_PNG, wx.BITMAP_TYPE_TIF,
                  wx.BITMAP_TYPE_JPEG, wx.BITMAP_TYPE_BMP, wx.BITMAP_TYPE_PNG]
                  
#------------------------------------------------------------------------------
class MyFrame(wx.Frame):
    def __init__(self, parent, title, filepath=None):
        wx.Frame.__init__(self, parent, -1, title,pos=(0,0),
                          style = wx.DEFAULT_FRAME_STYLE)
        self.Maximize()
        self.platform = self.getPlatform()
        #--------Set up Splitter and Notebook----------------------------------
        ## SPLITTER - contains drawing panel and playlist
        ## basepanel contains the splitter  
        self.basepanel = wx.Panel(self, style=wx.SUNKEN_BORDER)
                
        self.splitter = wx.SplitterWindow(self.basepanel, style=wx.SP_3D)
        self.splitter.SetMinimumPaneSize(10)
               
        # The windows inside the splitter are a
        # 1. canvas - A window in which all the drawing is done
        # 2. A notebook panel holding the playlist and notes
        self.canvas = Canvas(self.splitter)
        self.displayimage = DisplayImage(self)
        
        self.notebookpanel = wx.Panel(self.splitter, -1)
        self.nb = wx.Notebook(self.notebookpanel)
        self.notepadpanel = wx.Panel(self.nb, -1)
                
        self.listbox = AutoWidthListCtrl(self.nb)

        self.notepad = wx.TextCtrl(self.notepadpanel, -1,style=wx.TE_MULTILINE)
        
        self.nb.AddPage(self.listbox, "Playlist")
        self.nb.AddPage(self.notepadpanel, "Notes")

        # unsplit splitter for now, split later when size can be calculated
        self.splitter.SplitVertically(self.canvas,self.notebookpanel)
        self.splitter.Unsplit()
        
        #---- All the sizers --------------------------------------
        notebooksizer = wx.BoxSizer()
        notebooksizer.Add(self.nb, 1, wx.EXPAND, 0)
        self.notebookpanel.SetSizer(notebooksizer)
        
        notepadsizer = wx.BoxSizer()
        notepadsizer.Add(self.notepad, 1, wx.EXPAND, 0)
        self.notepadpanel.SetSizer(notepadsizer)
        
        splittersizer = wx.BoxSizer()
        splittersizer.Add(self.splitter, 1, wx.ALL|wx.EXPAND, 5)
        self.basepanel.SetSizer(splittersizer)

        #------------------------------
        self._buildMenuBar()
        self._buildToolBar()
        self.CreateStatusBar(3)
        #-------------------------------------
        self.Bind(wx.EVT_MENU, self.SelectFile, id=ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=ID_QUIT)
        self.Bind(wx.EVT_MENU, self.displayimage.SaveImage, id=ID_SAVE)
        self.Bind(wx.EVT_MENU, self.ToggleSplit, id=ID_UNSPLIT)
        self.Bind(wx.EVT_MENU, self.displayimage.RotateLeft, id=ID_ROTATELEFT)
        self.Bind(wx.EVT_MENU, self.displayimage.RotateRight, id=ID_ROTATERIGHT)
        self.Bind(wx.EVT_MENU, self.displayimage.ChooseCropFrame, id=ID_CROP)
        self.Bind(wx.EVT_MENU, self.canvas.NewCaliper, id=ID_CALIPER)
        self.Bind(wx.EVT_MENU, self.canvas.Calibrate, id=ID_CALIBRATE)
        self.Bind(wx.EVT_MENU, self.canvas.ToggleDoodle, id = ID_DOODLE)
        self.Bind(wx.EVT_MENU, self.SelectPrevImage, id = ID_PREVIOUS)
        self.Bind(wx.EVT_MENU, self.SelectNextImage, id = ID_NEXT)
        self.Bind(wx.EVT_MENU, self.canvas.ClearDoodle, id = ID_CLEAR)
        self.Bind(wx.EVT_MENU, self.About, id=ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.NewPlaylist, id=ID_NEWPL)
        self.Bind(wx.EVT_MENU, self.EditPlaylist, id=ID_EDITPL)
        self.Bind(wx.EVT_MENU, self.ListKeys, id=ID_KEYS)
        self.Bind(wx.EVT_MENU, self.editPref, id=ID_PREF)
        self.Bind(wx.EVT_MENU, self.canvas.RemoveAllCalipers, id=ID_CALIPERREMOVE)
        self.Bind(wx.EVT_MENU, self.ImportPresentation, id=ID_IMPORT)
        self.Bind(wx.EVT_MENU, self.ToggleFullScreen, id=ID_FULLSCREEN)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

        #self.listbox.Bind(wx.EVT_LEFT_DCLICK, self.JumptoImage)
        #self.listbox.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginEdit)
        self.listbox.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.JumptoImage)
        self.listbox.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndEdit)

        self.last_dir = '' # last dir used for file open

        # open file if specified as argument
        if filepath:
            self.load_new_file(filepath)
        
    def _buildMenuBar(self):
        """Build the menu bar"""
        self.MenuBar = wx.MenuBar()

        file_menu = wx.Menu()
        file_menu.Append(ID_OPEN, "&Open\tCtrl-O","Open file")
        file_menu.Append(ID_IMPORT, "&Import presentation\tCtrl-P",
                         "Experimental")
        file_menu.Append(ID_SAVE, "&Save\tCtrl-S","Save Image")
        file_menu.Append(ID_QUIT, "&Exit\tCtrl-Q","Exit")
   
        edit_menu = wx.Menu()
        edit_menu.Append(ID_FULLSCREEN, "FullScreen\tCtrl-F", "View fullscreen")
        edit_menu.Append(ID_CALIBRATE, "Cali&brate\tCtrl-B", "Calibrate image")
        edit_menu.Append(ID_CALIPER, "New &Caliper\tCtrl-C", "Start new caliper")
        edit_menu.Append(ID_CALIPERREMOVE, "Remove Calipers", "Remove all calipers")
        edit_menu.Append(ID_DOODLE, "&Doodle\tCtrl-D", "Doodle on the canvas")
        edit_menu.Append(ID_CLEAR, "Clear\tCtrl-X", "Clear the doodle")
        edit_menu.Append(ID_PREF, "Preferences", "Edit preferences")
        
        image_menu = wx.Menu()
        image_menu.Append(ID_ROTATELEFT, "Rotate &Left\tCtrl-L", "Rotate image left")
        image_menu.Append(ID_ROTATERIGHT, "Rotate &Right\tCtrl-R", "Rotate image right")
        image_menu.Append(ID_CROP, "Crop", "Crop the image")
        
        playlist_menu = wx.Menu()
        playlist_menu.Append(ID_PREVIOUS, "Previous\tPGUP", "Previous image")
        playlist_menu.Append(ID_NEXT, "Next\tPGDN", "Next image")
        playlist_menu.Append(ID_NEWPL, "New Playlist", 'Make New Playlist')
        playlist_menu.Append(ID_EDITPL, "Edit Playlist", 'Edit Playlist')
        
        help_menu = wx.Menu()
        help_menu.Append(ID_ABOUT, "About", "About this application")
        help_menu.Append(ID_KEYS, 'List keyboard shortcuts', 'Shortcuts')

        # popopu menu to appear with right click
        self.popup_menu = wx.Menu()
        self.popup_menu.Append(ID_ROTATELEFT, "Rotate Left", '')
        self.popup_menu.Append(ID_ROTATERIGHT, "Rotate Right", '')
        self.popup_menu.Append(ID_CROP, "Crop", "")
        self.popup_menu.Append(ID_CALIPERREMOVE, "Remove all Calipers", '')
        self.popup_menu.Append(ID_SAVE, "Save image", '')        

        
        self.MenuBar.Append(file_menu, "&File")
        self.MenuBar.Append(edit_menu, "&Edit")
        self.MenuBar.Append(image_menu, "&Image")
        self.MenuBar.Append(playlist_menu, "&Playlist")
        self.MenuBar.Append(help_menu, "&Help")
        
        self.SetMenuBar(self.MenuBar)

    def _buildToolBar(self):
        """Build the toolbar"""
        ## list of tools - can be made editable in preferences
        # (checktool?, id, "short help", "long help", "getimage name")
        tools = [
        #(False, ID_OPEN, "Open", "Open file", "open"),
        #(False, ID_SAVE, "Save", "Save file", "save"),
        (True, "SEP", '', '', ''),
        (False, ID_ROTATELEFT, "Rotate", "Rotate image left", "rotate_left"),
        (False, ID_ROTATERIGHT, "Rotate", "Rotate image right", "rotate_right"),
        (True,  ID_CROP, "Crop image", "Toggle cropping of image", "crop"),
        (True, "SEP", '', '', ''),
        (False, ID_CALIBRATE, "Calibrate", "calibrate image", "calibrate"),
        #(False, ID_CALIPER, "Caliper", "Start new caliper", "caliper"),
        (False, ID_CALIPERREMOVE, "Remove Calipers", "Remove all calipers", "caliper_remove"),
        (True, ID_DOODLE, "Doodle", "Doodle on canvas", "doodle"),
        (False, ID_CLEAR, "Clear", "Clear the doodle", "clear"),
        (True, "SEP", '', '', ''),
        (False, ID_PREVIOUS, "Previous", "Previous image", "previous"),
        (False, ID_NEXT, "Next", "Next image", "next"),
        (True, "SEP", '', '', ''),
        (False, ID_ABOUT, "About", "About this application", "about"),
        (False, ID_QUIT, "Quit", "Quit eepee", "quit"),
        (True, "SEP", '', '', ''),
        (True,  ID_UNSPLIT, "Close sidepanel", "Toggle sidepanel", "split")
            ]
        
        self.toolbar = self.CreateToolBar(wx.TB_HORIZONTAL|wx.NO_BORDER|
                                          wx.TB_FLAT)
        self.toolbar.SetToolBitmapSize((22,22))

        # use native icons on each platform for open and save only
        self.toolbar.AddLabelTool(ID_OPEN, "Open", wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN))
        self.toolbar.AddLabelTool(ID_SAVE, "Save", wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE))

        for tool in tools:
            checktool, id, shelp, lhelp, bmp = tool
            # separator
            if id == "SEP":
                self.toolbar.AddSeparator()
            # checktool
            elif checktool:
                self.toolbar.AddCheckLabelTool(id, shelp, getBitmap(bmp),
                                               longHelp=lhelp)
            # labeltool
            else:
                self.toolbar.AddLabelTool(id, shelp, getBitmap(bmp),
                                          longHelp=lhelp)
                
        self.toolbar.Realize()

    def About(self, event):
        """Display about message"""
        dlg = wx.MessageDialog(self, _about, "About Eepee", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()
     
    def editPref(self, event):
        """Edit preferences"""
        dlg = PreferenceDialog(self, -1, 'Edit preferences', self.canvas.configfile)
        dlg.ShowModal()
        
        self.canvas.config.readOptions()
        self.canvas.setOptions()
        
    def ListKeys(self, event):
        """List the keyboard shortcuts"""
        dlg = wx.MessageDialog(self, shortcuts, 'Shortcuts', wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def InitializeSplitter(self):
        """Initialize sash position"""
        # Do this for the first time when loading first image
        # For other images, it serves to reset sash position
        self.splitter.SplitVertically(self.canvas,self.notebookpanel)
        self.splitter.SetSashPosition(self.GetSize()[0] - 160)
    
    def ToggleSplit(self, event):
        """Unsplit or resplit the splitter"""
        if self.splitter.IsSplit():
            self.splitter.Unsplit()
        else:
            self.splitter.SplitVertically(self.canvas,self.notebookpanel)
            self.splitter.SetSashPosition(self.GetSize()[0] - 160, True)
        
        # if an image is loaded, trigger a redraw as canvas size changes
        if self.displayimage.image:
            self.canvas._BGchanged = True    

    def ToggleFullScreen(self, event):
        """Convert to full screen viewing of canvas"""
        if self.IsFullScreen():
            self.ShowFullScreen(False)
            self.splitter.SplitVertically(self.canvas,self.notebookpanel)
            self.splitter.SetSashPosition(self.GetSize()[0] - 160, True)
        else:
            if self.canvas.show_fullscreen_dialog:
                self.show_fscreen_help()
            self.ShowFullScreen(True, style=wx.FULLSCREEN_ALL)
            self.splitter.Unsplit()

    def show_fscreen_help(self):
        """Show a help dialog when switching to fullscreen"""
        dlg = help_dialog(self, -1, "Fullscreen help", '')
        dlg.ShowModal()
        if dlg.donotshowagain.GetValue():
            self.canvas.show_fullscreen_dialog = False
            self.canvas.config.options['show_fullscreen_dialog'] = 'False'
            self.canvas.config.writeOptions()
        
        dlg.Destroy()

    def getPlatform(self):
        """Find current platform"""
        platform = sys.platform
        if platform.startswith('linux'):
            return 'linux'
        elif platform == 'win32':
            return 'windows'
        elif platform == 'darwin':
            return 'mac'
        
        
    def SelectFile(self, event):
        """Triggered on opening file"""
        # selection dialog to select file
        # add playlist files to filter
        filter = 'Playlist|*.plst|' + accepted_wildcards

        if self.canvas.reuse_lastdir == 'True' and self.last_dir != '':
            dir2use = self.last_dir
        else:
            dir2use = self.canvas.default_dir

        print self.last_dir, dir2use

            
        dlg = wx.FileDialog(self, defaultDir = dir2use,
                            style=wx.OPEN, wildcard=filter)
        dlg.SetFilterIndex(5) #set 'all files' as default
        if dlg.ShowModal() == wx.ID_OK:
            filepath = dlg.GetPath()
            self.last_dir = os.path.dirname(filepath)
        else:
            return
        
        self.load_new_file(filepath)


    def load_new_file(self, filepath):
        """Load a new file, given the path to the file"""
        self.InitializeSplitter()
        self.playlist = PlayList(filepath)
        self.DisplayPlaylist()
        self.displayimage.LoadAndDisplayImage(filepath)


    def ImportPresentation(self, event):
        """import a presentation as a series of images
        that can be used in eepee"""
        filter = 'Presentation|*.ppt;*.pptx;*.odp|All files|*.*'
        dlg = wx.FileDialog(self, "Choose the presentation file",
                            style=wx.OPEN, wildcard=filter)
        if dlg.ShowModal() == wx.ID_OK:
            path_to_presentation = dlg.GetPath()
        else:
            return

        disposabledir = tempfile.mkdtemp()
        dlg = wx.DirDialog(self, "Choose folder to import to",
                           style=wx.OPEN, defaultPath=disposabledir)
        if dlg.ShowModal() == wx.ID_OK:
            target_folder = dlg.GetPath()
        else:
            return

        #osname = os.name
        #if osname == 'nt':
        if self.platform == 'windows':
            converter = Converter_MS(path_to_presentation, target_folder)
        #elif osname == 'posix':
        elif self.platform == 'linux':
            converter = Converter_OO(path_to_presentation, target_folder)
        
        self.DisplayMessage("Importing ...")
        try:
            converter.convert()
            self.DisplayMessage("")
        except ConverterError, msg:
            self.DisplayMessage("Failed import - %s" %(msg))
            return

        try:
            firstfile = glob.glob(os.path.join(target_folder, '*.jpg'))[0]
        except IndexError:
            self.DisplayMessage('Failed import')
            return
        self.InitializeSplitter()
        self.playlist = PlayList(firstfile)
        self.DisplayPlaylist()
        
        # load file
        self.displayimage.LoadAndDisplayImage(firstfile)

    def OnEndEdit(self, event):
        """User has edited a filename in the playlist window"""
        index = event.GetIndex()
        oldname = self.playlist.playlist[index]
        newname = os.path.join(os.path.dirname(oldname), event.GetLabel())

        if newname == oldname:
            pass
        elif os.path.exists(newname):
            self.DisplayMessage("Filename already exists!")
            self.listbox.SetStringItem(index, 0, os.path.basename(oldname)) # TODO
        else:
            st = shutil.move(oldname, newname)
            print st # TODO:
            self.DisplayMessage("Filename changed")
        
    def NewPlaylist(self, event):
        """Construct a new playlist"""
        playlist_selector = PlayListSelector(self, [])
        playlist_selector.ShowModal()
        
    def EditPlaylist(self, event):
        """Edit the current playlist"""
        playlist_selector = PlayListSelector(self, self.playlist.playlist)
        playlist_selector.ShowModal()
    
    def DisplayPlaylist(self):
        """Display a new playlist in the listbox"""
        #print dir(self.listbox)
        self.listbox.ClearAll()
        self.listbox.InsertColumn(0, 'Filename')
        for filename in self.playlist.playlist:
            index = self.listbox.InsertStringItem(sys.maxint,
                                                  os.path.split(filename)[1])
        self.listbox.SetItemState(self.playlist.nowshowing,
                                  wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
    
    def SelectNextImage(self,event):
        self.CleanUp()
        self.playlist.nowshowing += 1
        if self.playlist.nowshowing == len(self.playlist.playlist):
            self.playlist.nowshowing = 0
        self.listbox.SetItemState(self.playlist.nowshowing,
                                  wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

        self.displayimage.LoadAndDisplayImage(self.playlist.playlist[
                                                self.playlist.nowshowing])
        
    def SelectPrevImage(self,event):
        self.CleanUp()
        self.playlist.nowshowing -= 1
        if self.playlist.nowshowing == -1:
            self.playlist.nowshowing = len(self.playlist.playlist)-1
        self.listbox.SetItemState(self.playlist.nowshowing,
                                  wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

        self.displayimage.LoadAndDisplayImage(self.playlist.playlist[
                                                self.playlist.nowshowing])
       
    def JumptoImage(self,event):
        """On double clicking in listbox select that image"""
        self.CleanUp()
        self.playlist.nowshowing = self.listbox.GetNextSelected(-1)
        self.displayimage.LoadAndDisplayImage(self.playlist.playlist[
                                            self.playlist.nowshowing])
    
    def CleanUp(self):
        """Clean up on closing an image"""
        if self.displayimage.image:
            self.displayimage.CloseImage()
            
    def DisplayMessage(self, message):
        """Display the message in the status bar.
        Can be used to alert user about error messages"""
        self.SetStatusText(message, 0) #TODO: mechanism for alerting user
        
    
    def OnQuit(self, event):
        """On quitting the application"""
        self.CleanUp()
        sys.exit(0)

#------------------------------------------------------------------------------    
class AutoWidthListCtrl(wx.ListCtrl, ListCtrlAutoWidthMixin):
    def __init__(self, parent, *args, **kwargs):
        wx.ListCtrl.__init__(self, parent, -1,
                             style=wx.LC_REPORT|wx.LC_EDIT_LABELS|wx.LC_SINGLE_SEL)
        ListCtrlAutoWidthMixin.__init__(self)

        
#------------------------------------------------------------------------------    
class Canvas(wx.Window):
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1, style=wx.NO_FULL_REPAINT_ON_RESIZE)
        self.SetBackgroundColour('white')
        self.frame = wx.GetTopLevelParent(self)

        # User modifiable options
        self.configfile = self.getConfigfilepath()
        self.config =  Config(self.configfile)
        self.setOptions()                
        
        self.rubberband = RubberBand(self)
        self.doodle = Doodle(self)
            
        # Image height will always be 1000 units unless zoomed in
        self.maxheight = 1000
        
        # calibration  =   milliseconds / world_units
        self.calibration = 0  #0 means uncalibrated
        
        #one tool may be active at any time
        self.activetool = None
        
        # caliper list is a list of all calipers
        self.caliperlist = []
        self.activecaliperindex = -1 #only one caliper is active
        self.cursors = [wx.CURSOR_ARROW, wx.CURSOR_SIZEWE,
                        wx.CURSOR_HAND]        
        # flag to check if image is loaded
        self.resizedimage = None
        
        self._BGchanged = False
        self._FGchanged = False
        
        self.Bind(wx.EVT_SIZE, self.OnResize)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_MOUSE_EVENTS, self.OnMouseEvents)

        # On windows, the onpaint function is required to
        # handle paint events properly. However, it produces some artifacts
        # during canvas initiation in Linux - so compromising my delaying the
        # binding by 1 second seems to work        
        wx.FutureCall(1000, self.BindOnPaint)
    
    def getConfigfilepath(self):
        """Depending on os, get the path to the config file"""
        #if os.name == 'nt':
        if self.frame.platform == 'windows':
            return 'config.ini'
        #elif os.name == 'posix':
        elif self.frame.platform in ['linux', 'mac']: #TODO: same for mac ?
            return os.path.expanduser('~/.eepee.rc')

    
    def setOptions(self):
        """Depending on the prefs stored in the config file,
        set the options"""
        self.default_dir = self.config.options.get('default_dir')
        self.reuse_lastdir = self.config.options.get('reuse_dir')
        self.caliper_width = int(self.config.options.get('caliper_width'))
        self.caliper_color = self.config.options.get('caliper_color')
        self.caliper_shape = self.config.options.get('caliper_shape')
        self.active_caliper_color = self.config.options.get('active_caliper_color')
        self.doodle_width = int(self.config.options.get('doodle_width'))
        self.doodle_color = self.config.options.get('doodle_color')

        self.show_fullscreen_dialog = self.config.options.get(
            'show_fullscreen_dialog', 'True') == 'True'
        
        measurement = self.config.options.get('caliper_measurement')
        if measurement == 'Time':
            self.timedisplay = True
            self.ratedisplay = False
        elif measurement == 'Rate':
            self.timedisplay = False
            self.ratedisplay = True
        elif measurement == 'Both':
            self.timedisplay = True
            self.ratedisplay = True
        elif measurement == 'None':
            self.timedisplay = False
            self.ratedisplay = False
       
    def BindOnPaint(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint) 

    def handleMouseEvents(self, event):
        """handle mouse events when no tool is active"""
        if self.resizedimage:
            pos = event.GetPosition()
            worldx, worldy = (self.PixelsToWorld(pos.x, 'xaxis'),
                              self.PixelsToWorld(pos.y, 'yaxis'))
            
            if event.Moving():
                # check for hitobject and mark them
                caliper, caliperindex, hit_type = self.HitObject(worldx, worldy)
                    
            elif event.LeftDown():
                # check for hit object and activate it
                caliper, caliperindex, hit_type = self.HitObject(worldx, worldy)
                if caliper:
                    self.activetool = 'caliper'
                    self.activecaliperindex = caliperindex
                    if hit_type == 1:
                        #flip the caliper legs, then just move second leg
                        caliper.x1, caliper.x2 = caliper.x2, caliper.x1
                        caliper.state = 2
                        self.SetCursor(wx.StockCursor(self.cursors[1]))
                    elif hit_type == 2: #move second leg
                        caliper.state = 2
                        self.SetCursor(wx.StockCursor(self.cursors[1]))

                    elif hit_type == 3: #move whole caliper
                        caliper.x1offset = worldx - caliper.x1
                        caliper.x2offset = caliper.x2 - worldx
                        caliper.state = 4
                        self.SetCursor(wx.StockCursor(self.cursors[2]))

                else: # if left click was not to select pre-existing
                    # caliper, start a new one
                    self.NewCaliper(event)
                        
            elif event.RightDown():
                # if caliper hittable - delete it
                caliper, caliperindex, hit_type = self.HitObject(worldx, worldy)
                if caliper:
                    self.caliperlist.remove(caliper)
                    self._FGchanged = True
                    
                # else, popup menu
                else:
                    self.frame.PopupMenu(self.frame.popup_menu, event.GetPosition())
        else:
            pass
        
    def OnResize(self, event):
        """canvas resize triggers bgchanged flag so that it will
        be redrawn on next idle event"""
        # update / initialize height and width
        self.width, self.height = self.GetSize()
        
        # update / create the buffer for the buffered dc
        image = wx.EmptyImage(self.width, self.height)
        wx.Image.Create(image,self.width, self.height, False)
        wx.Image.SetRGBRect(image, wx.Rect(0, 0, self.width, self.height),
                            255, 255, 255)        
        self.buffer = wx.BitmapFromImage(image)
        
        if self.resizedimage: # only if image is loaded
            self._BGchanged = True
        
    def OnIdle(self, event):
        """Redraw if there is a change"""

        if self._BGchanged or self._FGchanged:
            dc = wx.BufferedDC(wx.ClientDC(self), self.buffer,
                               wx.BUFFER_CLIENT_AREA)
            dc.Clear()  #clear old image if still there        
        
        if self._BGchanged:
            self.ProcessBG()
            self.Draw(dc)
           
        elif self._FGchanged:
            self.Draw(dc)

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.buffer)

        
    def OnMouseEvents(self, event):
        """Handle mouse events depending on active tool"""
        
        if self.activetool == None: 
            self.handleMouseEvents(event)
        
        # ----- Rubberband -------------------------------
        elif self.activetool == "rubberband":
            if event.LeftUp(): # finished selecting crop extent
                # convert cropframe to list to make it easier to manipulate
                cropframe = list(self.rubberband.getCurrentExtent())

                self.rubberband.reset()
                self.SetCursor(wx.NullCursor)
                self.activetool = None
                
                self.frame.displayimage.image = \
                    self.frame.displayimage.CropImage(cropframe)
                self.resetFG()
                self._BGchanged = True
                
            else:
                self.rubberband.handleMouseEvents(event)
          
        #------- Caliper ----------------------------------      
        elif self.activetool == "caliper":
            # hand the event to the active caliper
            self.caliperlist[self.activecaliperindex].handleMouseEvents(event)
            
        # --------- Calibrate ----------------------------
        elif self.activetool == "calibrate":
            self.calibrate_caliper.handleMouseEvents(event)
            
        # ----------- Doodle------------------
        elif self.activetool == "doodle":
            self.doodle.handleMouseEvents(event)
        

    def PixelsToWorld(self, coord, axis):
        """convert from pixels to world units.
         coord is a single value and axis denoted
         axis to which it belongs (x or y)"""
        if axis == 'xaxis':
            return round((coord - self.xoffset) * self.factor)
        elif axis == 'yaxis':
            return round((coord - self.yoffset) * self.factor)
    
    def WorldToPixels(self, coord, axis):
        """convert from world units to pixels.
         coord is a single value and axis denoted
         axis to which it belongs (x or y)"""
        if axis == 'xaxis':
            return (coord / self.factor) + self.xoffset
        elif axis == 'yaxis':
            return (coord / self.factor) + self.yoffset
        
    def ProcessBG(self):
        """Process the image by resizing to best fit current size"""
        image = self.frame.displayimage.image
        imagewidth, imageheight = image.size
        
        # What drives the scaling - height or width
        if imagewidth / imageheight > self.width / self.height:
            self.scalingvalue = self.width / imagewidth
        else:
            self.scalingvalue = self.height / imageheight
        
                
        # resize with antialiasing
        self.resized_width =  int(imagewidth * self.scalingvalue)
        self.resized_height = int(imageheight * self.scalingvalue)
        self.resizedimage = image.resize((self.resized_width,
                                          self.resized_height)
                                             , Image.ANTIALIAS)
        
        # factor chosen so that image ht = 1000 U
        self.factor = self.maxheight / self.resized_height
        
        # blit the image centerd in x and y axes
        self.bmp = self.ImageToBitmap(self.resizedimage)
        self.imagedc = wx.MemoryDC()
        self.imagedc.SelectObject(self.bmp)
        
        self.xoffset = (self.width-self.resized_width)/2
        self.yoffset = (self.height-self.resized_height)/2
            
    def Draw(self, dc):
        """Redraw the background and foreground elements"""
        # blit the buffer on to the screen - BG
        dc.Blit(self.xoffset, self.yoffset,
                self.resized_width, self.resized_height, self.imagedc, 0, 0)
        
        # draw the calipers
        for caliper in self.caliperlist:
            caliper.draw(dc)
        
        # doodle lines
        self.doodle.Draw(dc)
        
        self._BGchanged = False 
        self._FGchanged = False
        #self._doodlechanged = False
    
    def DrawDoodle(self, dc):
        """Draw the doodle lines without redrawing everything else"""
        self.doodle.Draw(dc)
        #self._doodlechanged = False
    
    def ClearDoodle(self , event):
        self.doodle.lines = []
        self._FGchanged = True
        #self._doodlechanged = True
    
    def resetFG(self):
        """When the coords are not preserved, reset all
        foreground elements to default"""
        self.doodle.lines = []
        self.caliperlist = []
        self.calibration = 0
        self.frame.SetStatusText("Not calibrated", 2)
        
    def ImageToBitmap(self, img):
        newimage = apply(wx.EmptyImage, img.size)
        newimage.SetData(img.convert( "RGB").tostring())
        bmp = newimage.ConvertToBitmap()
        return bmp
    
    def NewCaliper(self, event):
        """Start a new caliper"""
        self.caliperlist.append(Caliper(self, self.caliper_shape))
        self.activecaliperindex = len(self.caliperlist)-1
        self.activetool = "caliper"

    def RemoveAllCalipers(self, event):
        """Remove all the existing calipers"""
        self.caliperlist = []
        self._FGchanged = True
        
    def Calibrate(self, event):
        """Calibrate / recalibrate image"""
        self.calibrate_caliper = CalibrateCaliper(self)
        self.caliperlist.append(self.calibrate_caliper)
        self.activetool = "calibrate"
        self.activecaliperindex = len(self.caliperlist)-1
        
    def HitObject(self, worldx, worldy):
        """Find the object that is hittable.
        This is the object within a defined distance from the given coords"""
        # find if any caliper is hittable
        for caliperindex, caliper in enumerate(self.caliperlist):
            hittable = caliper.isHittable(worldx, worldy)
            if hittable > 0:
                return (caliper, caliperindex, hittable)
        
        # if nothing is hit
        return (None, 0, 0)
    
    def ToggleDoodle(self, event):
        """Toggle doodle on or off"""
        if self.activetool == "doodle":
            self.activetool = None
            self.frame.toolbar.ToggleTool(ID_DOODLE, 0)
            
        else:
            self.activetool = "doodle"
            self.frame.toolbar.ToggleTool(ID_DOODLE, 1)
            
    def TranslateFrame(self, frame, rotation, imagewidth, imageheight):
        """Utility function to translate frame coordinates according
        to rotation in multiples of 90 degrees. Frame is tuple (x1, y1, x2, y2).
        """
        rotation = rotation % 4 # make it modulo 4
        [x1, y1, x2, y2] = frame
        
        if rotation == 0:
            return frame
        
        elif rotation  == 1:
            return [y1, imagewidth-x2, y2, imagewidth-x1]
        
        elif rotation == 2:
            return [imagewidth-x2, imageheight-y2,
                    imagewidth-x1, imageheight-y1]
        
        elif rotation == 3:
            return [imageheight-y2, x1, imageheight-y1, x2]
            
       
#------------------------------------------------------------------------------

class DisplayImage():
    """The display image and associated functions"""
    def __init__(self, parent):
        self.frame = parent
        self.canvas = self.frame.canvas
        
        self.image = None # will be loaded

        # image cropping can be toggled
        # if prev crop info is stored, this will be true
        self.iscropped = False
        self.cropframe = [0,0,0,0] # x1, y1, x2, y2
        
        # conversion factor to convert from px to world coords
        # = 1000 / image height in px
        self.factor = 0
        
        # keep a counter of rotation state, so that it can be saved
        self.rotation = 0
        
        # default data
        self.defaultdata = {"note" : '', "calibration" : 0,
                            "rotation" : 0, "cropframe" : [0,0,0,0]}
        
        # data saved with image
        self.data = None #ToDO : may not require
        
    def LoadAndDisplayImage(self, filepath):
        """Load a new image and display"""
        self.filepath = filepath

        # handle .plst files
        if self.filepath.endswith('.plst'):
            try:
                self.filepath = self.frame.playlist.playlist[0]
            except IndexError:
                self.frame.DisplayMessage("Empty playlist")
                return
            
        try:        
            self.uncropped_image = Image.open(self.filepath, 'r')
        except:
            # TODO: catch specific errors and display error message
            self.frame.DisplayMessage("Could not load image")
            return

        # load saved information
        self.ResetData()
        self.LoadImageData()
        
        # crop image as per saved frame
        if self.iscropped:
            self.image = self.uncropped_image.crop(self.cropframe)
            self.frame.toolbar.ToggleTool(ID_CROP, 1)
            #self.image = self.CropImage(self.cropframe, "image")
        else:
            self.image = self.uncropped_image
        
        # rotate image to match saved rotation
        self.image = self.Rotate(self.image, self.rotation)
            
        self.canvas._BGchanged = True
        
        # update statusbar messages
        self.frame.SetStatusText(os.path.split(self.filepath)[1], 1)
        if self.canvas.calibration != 0:
            self.frame.SetStatusText("Calibrated", 2)
        else:
            self.frame.SetStatusText("Not Calibrated", 2)
    
    def LoadImageData(self):
        """Load the stored data for the image at filepath"""
        # data is stored pickled with pathname same as image with
        # '.' in front (hidden on Linux) and '.pkl' as extension
        self.datafile = os.path.join(os.path.dirname(self.filepath),
                  "."+os.path.splitext(os.path.basename(self.filepath))[0]+".pkl")
        if os.path.exists(self.datafile):
            self.data = pickle.load(open(self.datafile,'r'))
       
        # load the variables with default vals if key does not exist
        self.note = self.data.get("note", '')
        self.frame.notepad.SetValue(self.note)
        self.canvas.calibration = self.data.get("calibration", 0)
        self.rotation = self.data.get("rotation", 0)
        self.cropframe = self.data.get("cropframe", [0,0,0,0])       
            
        # for compatibility with older versions where cropframe was tuple
        self.cropframe = list(self.cropframe)
        
        if self.cropframe != [0,0,0,0]:
            self.iscropped = True
            
        self.loaded_data = copy.deepcopy(self.data)
        
    def ResetData(self):
        """Reset image data when new image is loaded"""
        # reset data to default
        self.data = copy.deepcopy(self.defaultdata)
        
        # clear the doodle
        self.canvas.ClearDoodle(None)
        
        self.iscropped = False
        self.frame.toolbar.ToggleTool(ID_CROP, 0)
            
        self.canvas.activetool = None
        self.frame.toolbar.ToggleTool(ID_DOODLE, 0)
        
    def SaveImageData(self):
        """Save the image data - but only if data has changed"""
        # if data is None, initialise as empty dict
        if not self.data:
            self.data = {}
        
        # collect all data
        self.data["note"] = self.frame.notepad.GetValue() 
        self.data["calibration"] = self.canvas.calibration
        self.data["rotation"] = self.rotation % 4 # modulo 4 - remove extra loops
        self.data["cropframe"] = self.cropframe

        # save data if it has changed
        if self.data != self.loaded_data:
            try:
                #if os.name == 'posix':
                if self.frame.platform in ['linux', 'mac']:
                    pickle.dump(self.data, open(self.datafile, 'w'))

                # in windows, set file attribute to hidden
                #elif os.name == 'nt':
                elif self.frame.platform == 'windows':
                    ## have to remove the hidden file because it doesnt have
                    ## write permission
                    if os.path.exists(self.datafile):
                        os.remove(self.datafile)  
                    pickle.dump(self.data, open(self.datafile, 'w'))
                    status = os.popen("attrib +h \"%s\"" %(self.datafile))
                    if status != 0:
                        pass

            except:
                self.frame.DisplayMessage("Could not save image data for %s" %(
                        os.path.basename(self.filepath)))
                
        
    def SaveImage(self, event):
        """
        Save the modified DC as an image.
        Initialize a memoryDC as an empty bitmap and blit the clientdc 
        to it. Then we can disconnect the bitmap from the memory dc
        and save it. 
        """
        # copy the clientDC out before getting the savefilename because
        # the 'shadow' of the save dialog results in a white area on the
        # saved image.
        context = wx.ClientDC(self.canvas)
        savebmp = wx.EmptyBitmap(self.canvas.width,self.canvas.height)
        #convert dc to bitmap
        memdc = wx.MemoryDC()
        memdc.SelectObject(savebmp)
        memdc.Blit(0,0,self.canvas.width,self.canvas.height,context,0,0)
        memdc.SelectObject(wx.NullBitmap)

        dlg = wx.FileDialog(self.frame, "Save image as...", 
                            defaultDir = self.canvas.default_dir,
                            style=wx.SAVE | wx.OVERWRITE_PROMPT,
                            wildcard=accepted_wildcards)
        if dlg.ShowModal() == wx.ID_OK:
            savefilename = dlg.GetPath()
            filter_index = dlg.GetFilterIndex()
            dlg.Destroy()
        else:
            dlg.Destroy()
            return
        
        # format to save is dependent on selected wildcard, default to png
        
        # Looks like the extension is added automatically on windows
        #if os.name == 'posix':
        if self.platform == 'windows':
            savefilename += accepted_formats[filter_index]
        
        try:
            savebmp.SaveFile(savefilename, image_handlers[filter_index])
        except:
            self.frame.DisplayMessage("Could not save image")
    
    def RotateLeft(self, event):
        """Rotate the image 90 deg counterclockwise.
        Will reset the world coordinates"""
        self.image = self.image.transpose(Image.ROTATE_90)
        self.rotation -= 1
        self.canvas.resetFG() # since coords have changed
        self.canvas._BGchanged = True
        
    def RotateRight(self, event):
        """Rotate the image 90 deg clockwise.
        Will reset the world coordinates"""
        self.image = self.image.transpose(Image.ROTATE_270)
        self.rotation += 1
        self.canvas.resetFG() # since coords have changed
        self.canvas._BGchanged = True
        
    def Rotate(self, image, rotation):
        """Handle rotation of 90, 180 and 270 degrees"""
        rotation = rotation % 4
        
        if rotation == 0:
            pass
        elif rotation == 1:
            image = image.transpose(Image.ROTATE_270)
        elif rotation == 2:
            image = image.transpose(Image.ROTATE_180)
        elif rotation == 3:
            image = image.transpose(Image.ROTATE_90)
            
        return image
        
    def ChooseCropFrame(self, event):
        """Choose the frame to crop image using a rubberband"""
        if not self.iscropped:
            self.canvas.activetool = "rubberband"
        
        else:
            # uncrop - reset crop frame, but rotate to current state
            self.image = self.uncropped_image
            self.image = self.Rotate(self.image, self.rotation)
            self.cropframe = [0,0,0,0]
            self.canvas.resetFG()
            self.iscropped = False
            self.canvas._BGchanged = True
        
    def CropImage(self, cropframe):
        """Crop the image. Crop frame is the outer frame"""
        
        # cropframe coords are derived from rubberband
        # They are in reference to canvas.
        # remove offsets so that they refer to image, then
        # scale so that they reflect pixels
        cropframe = [cropframe[0] - self.canvas.xoffset,
                     cropframe[1] - self.canvas.yoffset,
                     cropframe[2] - self.canvas.xoffset,
                     cropframe[3] - self.canvas.yoffset]
        self.cropframe = [int(coord/self.canvas.scalingvalue)
                                      for coord in cropframe]

        # correct cropframe for current rotation of canvas so that cropframe
        # applies to unrotated image
        
        # obtain size of 'original image' in current orientation
        width, height = self.uncropped_image.size
        if self.rotation % 2 == 1: # odd rotation means w and h are swapped
            width, height = height, width
        
        # translate cropframe to unrotated image
        self.cropframe = self.canvas.TranslateFrame(self.cropframe,
                                        self.rotation, width, height)
        
        # convert any negative value to 0
        for ind, val in enumerate(self.cropframe):
            if val < 0:
                self.cropframe[ind] = 0
        
        # now crop and rotate
        cropped_image = self.uncropped_image.crop(self.cropframe)
        cropped_rotated_image = self.Rotate(cropped_image, self.rotation)
        
        self.iscropped = True
        self.canvas._BGchanged = True
        
        return cropped_rotated_image
        
    def CloseImage(self):
        """Things to do before closing image"""
        self.SaveImageData()
        # TODO: based in user preference may clear calipers

#------------------------------------------------------------------------------
class Caliper():
    """Caliper is a tool with two vertical lines connected by a bridge"""
    def __init__(self, canvas, shape='full'):
        """
        Full caliper is as shown below
        Truncated caliper (shape = 'truncated') has short legs
        """
        self.canvas = canvas
        self.shape = shape

        # coordinates are in 'world coordinates'
        #          x1,y1    x2y1
        #           |       |
        #     x1,y2 |_______| x2,y2
        #           |       |
        #         x1,y3     x2,y3
        #
        # default coordinates
        self.x1, self.x2 = 0, 0
        self.y1, self.y2 = 0, 0
        self.y3 = self.canvas.maxheight

        self.pen = wx.Pen(self.canvas.caliper_color, self.canvas.caliper_width, wx.SOLID)
        self.hittable_pen = wx.Pen(self.canvas.active_caliper_color,
                                   self.canvas.caliper_width, wx.SOLID)
        
        # 1 - positioning first caliperleg, 2 - positioning second caliperleg
        # 3 - positioned both caliperlegs, 4 - repositioning whole caliper
        # cycle 1 -> 2 -> 3 -> 2 or 4 -> 3
        self.state = 1
        
        # range from mouse to be hittable
        self.hitrange = 10
        self.was_hittable = False # true if it becomes hittable
        # distance between legs
        self.measurement = 0
        
    def draw(self,dc):
        """draw the caliper on the canvas"""
        dc.BeginDrawing()
        dc.SetPen(self.pen)
        
        # convert to pixels for drawing
        x1 = self.canvas.WorldToPixels(self.x1, "xaxis")
        x2 = self.canvas.WorldToPixels(self.x2, "xaxis")
        y1 = self.canvas.WorldToPixels(self.y1, "yaxis")
        y2 = self.canvas.WorldToPixels(self.y2, "yaxis")
        y3 = self.canvas.WorldToPixels(self.y3, "yaxis")

        # truncated caliper
        if self.shape == 'truncated':
            y1 = max(y1, y2-(y3*0.05))
            y3 = min(y3, y2+(y3*0.05))
        
        # draw the lines
        dc.DrawLine(x1, y1, x1, y3) # left vertical
        dc.DrawLine(x2, y1, x2, y3) # right vertical
        dc.DrawLine(x1, y2, x2, y2) # horiz
        
        self.MeasureAndDisplay(dc)
        dc.EndDrawing()
        
    def MeasureAndDisplay(self, dc):
        # write measurement
        if self.state > 1:
            self.measurement = abs(self.x2 - self.x1) #world coords
            measurement_units = 'units'
            if self.canvas.calibration > 0:
                self.measurement *= self.canvas.calibration
                measurement_units = 'ms'
                
                if self.canvas.ratedisplay: # will display rate only if calibrated
                    rate = 60000 / self.measurement
                    dc.DrawText('%s bpm' %(int(rate)),
                       self.canvas.WorldToPixels((self.x1 + self.x2)/2,'xaxis'),
                       self.canvas.WorldToPixels(self.y2 + 40, 'yaxis'))
            
            if self.canvas.timedisplay:
                dc.DrawText('%s %s' %(int(self.measurement), measurement_units),
                           self.canvas.WorldToPixels((self.x1 + self.x2)/2,'xaxis'),
                           self.canvas.WorldToPixels(self.y2 - 40, 'yaxis'))
        
        
    def handleMouseEvents(self, event):
        """Mouse event handler when caliper is the active tool"""
        # get mouse position in world coords
        pos = event.GetPosition()
        mousex, mousey = (self.canvas.PixelsToWorld(pos.x, 'xaxis'),
                          self.canvas.PixelsToWorld(pos.y, 'yaxis'))
        
        # cancel caliper anytime by right clicking
        if event.RightDown():
            self.canvas.caliperlist.pop(-1)
            self.canvas._FGchanged = True
            self.canvas.activetool = None
        
        # beginning - this is first caliper being positioned
        elif event.Moving() and self.state == 1:
            self.x1 = self.x2 = mousex
            self.y2 = mousey
            self.canvas._FGchanged = True
        
        # fix the first caliper
        elif event.LeftDown() and self.state == 1:
            self.state = 2
            
        # positioning second caliper
        elif event.Moving() and self.state == 2:
            self.x2 = mousex
            self.y2 = mousey
            self.canvas._FGchanged = True
            
        # fix second caliper
        elif event.LeftDown() and self.state == 2:
            self.state = 3
            self.canvas.SetCursor(wx.StockCursor(self.canvas.cursors[0]))
            self.OnCompletion()
            self.canvas.activetool = None
        
        # move whole caliper
        elif event.Moving() and self.state == 4:
            self.x1 = mousex - self.x1offset
            self.x2 = mousex + self.x2offset
            self.y2 = mousey
            self.canvas._FGchanged = True
        
        # stop moving whole caliper
        elif event.LeftDown() and self.state == 4:
            self.state = 3
            self.canvas.SetCursor(wx.StockCursor(self.canvas.cursors[0]))
            self.canvas.activetool = None
            self.activetool = None
        
        else:
            pass

    def isHittable(self, worldx, worldy):
        """Is it within hitting range from current mouse position"""
        if abs(worldx - self.x1) < self.hitrange:
            if not self.was_hittable:
                self.MarkAsHittable(1)
            return 1 #first leg
        
        elif abs(worldx - self.x2) < self.hitrange:
            if not self.was_hittable:
                self.MarkAsHittable(2)
            return 2 #second leg
        
        elif abs(worldy - self.y2) < self.hitrange and \
             sorted([worldx, self.x1, self.x2])[1] == worldx:
            # if mouse x is between x1 and x2
            if not self.was_hittable:
                self.MarkAsHittable(3)
            return 3 #horizontal (whole caliper)
        
        else:
            if self.was_hittable:
                self.was_hittable = False
                self.canvas._FGchanged = True
            return 0
        
    def MarkAsHittable(self, type):
        """Mark caliper as hittable.
        type is 1 for first leg, 2 for second leg and 3 for whole"""
        dc = wx.BufferedDC(wx.ClientDC(self.canvas),
                           self.canvas.buffer, wx.BUFFER_CLIENT_AREA)
        dc.BeginDrawing()
        dc.SetPen(self.hittable_pen)
        
        x1 = self.canvas.WorldToPixels(self.x1, "xaxis")
        x2 = self.canvas.WorldToPixels(self.x2, "xaxis")
        y1 = self.canvas.WorldToPixels(self.y1, "yaxis")
        y2 = self.canvas.WorldToPixels(self.y2, "yaxis")
        y3 = self.canvas.WorldToPixels(self.y3, "yaxis")

        # truncated caliper
        if self.shape == 'truncated':
            print 'yes'
            y1 = max(y1, y2-(y3*0.05))
            y3 = min(y3, y2+(y3*0.05))

        
        if type == 1:
            dc.DrawLine(x1, y1, x1, y3) # left vertical
        elif type == 2:
            dc.DrawLine(x2, y1, x2, y3) # right vertical
        elif type == 3:
            dc.DrawLine(x1, y1, x1, y3) # left vertical
            dc.DrawLine(x2, y1, x2, y3) # right vertical
            dc.DrawLine(x1, y2, x2, y2) # horiz
        
        dc.EndDrawing()
        self.was_hittable = True
        
    def OnCompletion(self):
        """Things to do on completion of one caliper.
        Only a placeholder here for now"""
        pass
    
#------------------------------------------------------------------------------
class CalibrateCaliper(Caliper):
    """A special caliper used for calibration"""
    def __init__(self, parent):
        Caliper.__init__(self, parent)
        self.canvas = parent
        
        # default coordinates
        self.x1, self.x2 = 0, 0
        self.y1, self.y2 = 0, 0
        self.y3 = self.canvas.maxheight
        
        self.pen = wx.Pen(wx.Colour(0, 0, 0), 1, wx.SOLID)
        self.state = 1
        self.measurement = 0
        
    def OnCompletion(self):
        # get calibration entry
        calibration = self.GetUserEntry("Enter distance in ms:")
        
        # handle cancel
        if calibration == None:
            self.canvas.caliperlist.pop(-1)
            self.canvas._FGchanged = True
            return
        
        # handle invalid entry
        while not calibration.isdigit():
            calibration = (self.GetUserEntry
                          ("Please enter a positive number"))
            if calibration == None: # if user cancels, remove caliper
                self.canvas.caliperlist.pop(-1)
                self.canvas._FGchanged = True
                return
                
        # set canvas calibration
        self.canvas.calibration = int(calibration) / self.measurement
        
        # set status text in frame
        self.canvas.frame.SetStatusText("Calibrated", 2)
        
        # remove calibrate_caliper
        self.canvas.caliperlist.pop(-1)
        self.canvas._FGchanged = True
    
    def MeasureAndDisplay(self, dc):
        # for calibration, measurement is always raw measurement
        # and is not displayed
        if self.state > 1:
            self.measurement = abs(self.x2 - self.x1) #world coords
            
    def GetUserEntry(self,message):
        """Get entry from user for calibration.
        Entry must be a positive integer"""
        calib = 0
        dialog = wx.TextEntryDialog(None,\
                                   message,"Calibrate")
        if dialog.ShowModal() == wx.ID_OK:
            calibration = dialog.GetValue()
            dialog.Destroy()
            return calibration
        else: # On cancel
            return None
        
#-------------------------------------------------------------------------
class Doodle():
    """Doodle on the image canvas"""
    def __init__(self, parent):
        self.lines = [] #list of doodle coords
        self.canvas = parent
        self.pen =wx.Pen(self.canvas.doodle_color, self.canvas.doodle_width, wx.SOLID)
        
    def Draw(self, dc):
        """Draw the lines for the doodle"""
        dc.SetPen(self.pen)
        for line in self.lines: # line is a list of tuples
            for coords in line:
                x1 = self.canvas.WorldToPixels(coords[0], 'xaxis')
                y1 = self.canvas.WorldToPixels(coords[1], 'yaxis')
                x2 = self.canvas.WorldToPixels(coords[2], 'xaxis')
                y2 = self.canvas.WorldToPixels(coords[3], 'yaxis')
                dc.DrawLine(*(x1, y1, x2, y2))
                
    def DrawLine(self, coords):
        """Draw the last bit of line"""
        dc = wx.BufferedDC(wx.ClientDC(self.canvas), self.canvas.buffer,
                               wx.BUFFER_CLIENT_AREA)
        dc.SetPen(self.pen)
        dc.DrawLine(*coords)
                
    def handleMouseEvents(self, event):
        """Handle all mouse events when active"""
        pos = event.GetPosition()
        mousex, mousey = (self.canvas.PixelsToWorld(pos.x, 'xaxis'),
                          self.canvas.PixelsToWorld(pos.y, 'yaxis'))
        if event.LeftDown():
            """Start a new line on left click"""
            self.current_line = []
            self.oldx = mousex
            self.oldy = mousey
        
        elif event.Dragging() and event.LeftIsDown():
            """Draw the line"""
            coords = (mousex, mousey, self.oldx, self.oldy)
            
            x1 = self.canvas.WorldToPixels(coords[0], 'xaxis')
            y1 = self.canvas.WorldToPixels(coords[1], 'yaxis')
            x2 = self.canvas.WorldToPixels(coords[2], 'xaxis')
            y2 = self.canvas.WorldToPixels(coords[3], 'yaxis')
            
            # stored lines will have world coords - draw as pixels
            self.current_line.append(coords)
            self.DrawLine((x1, y1, x2, y2))

            self.oldx = mousex
            self.oldy = mousey
    
        elif event.LeftUp():
            """End current line"""
            self.lines.append(self.current_line)    
    
    def Clear(self, event):
        self.lines = []
        self.window.Refresh()
        

#--------------------------------------------------------------------------
class PlayList():
    """The list of image files to show"""
    def __init__(self,filename):
        """Initialize when a file is opened"""
        self.playlist = []
        self.nowshowing = 0   #current position in list
        
        # Open playlist file
        if filename.endswith('.plst'):
            self.playlistfile = filename
            self.OpenPlaylist()
        
        # Or an image file (already filtered at selection)
        else:
            self.CreatePlayList(filename)
    
    def CreatePlayList(self, filename):
        """
        Make a playlist by listing all image files in the directory beginning
        from the selected file
        """
        dirname,currentimage = os.path.split(filename)
        allfiles = os.listdir(dirname)
                
        for eachfile in allfiles:
            if os.path.splitext(eachfile)[1].lower() in ['.bmp','.png',
                                        '.jpg','.jpeg','.tif','.tiff']:
                self.playlist.append(os.path.join(dirname,eachfile))
        self.playlist.sort()
        self.nowshowing = self.playlist.index(filename)
                        
    def OpenPlaylist(self):
        """open an existing playlist"""
        try:
            self.playlist = [path.rstrip('\n') for path in
                             open(self.playlistfile, 'r').readlines()]
        except:
            pass # TODO: display error in frame

#------------------------------------------------------------------------------        
class MyApp(wx.App):
    def OnInit(self):
        filepath = None
        if len(sys.argv) > 1:
            filepath = sys.argv[1]
        if filepath:
            frame = MyFrame(None, _title, filepath)
        else:
            frame = MyFrame(None, _title)
        frame.Show(1)
        self.SetTopWindow(frame)
        return 1
#------------------------------------------------------------------------

def main():
    app = MyApp(0)
    app.MainLoop()


if __name__ == "__main__":
    main()
