#!/usr/bin/env python

"""Subclass of wx.dialog where user can choose not to
see dialog again"""
import wx

class help_dialog(wx.Dialog):
    def __init__(self, parent,id, title, msg):
        wx.Dialog.__init__(self, parent,id, title)
        #self.panel = wx.Panel(self, -1)

        self.message = wx.StaticText(self, 11, "\n".join([
                    "  You are about to enter fullscreen viewing mode.  ",
                    "  You can press Ctrl-F to exit fullscreen anytime.  ",
                    "",
                    "  Other useful keybindings are - ",
                    "  Ctrl-o  - Open file  ",
                    "  Ctrl-r  - Rotate right  ",
                    "  Ctrl-l  - Rotate left  ",
                    "  Ctrl-b  - Calibrate  ",
                    "  Ctrl-d  - Start/stop doodle  ",
                    "  Ctrl-x  - Clear doodle  ",
                    "  PgDn    - Next image  ",
                    "  PgDn    - Prev image  ",
                    "  Ctrl-q  - Quit\n  ",
                    "  Left click - Start new caliper  ",
                    "  Right click - Removes caliper  \n\n" ]))
        
        self.donotshowagain = wx.CheckBox(self,  -1,"Do not show this message again")
        self.okButton = wx.Button(self, wx.ID_OK, "OK")

        self.sizer = self.CreateTextSizer('')
        
        #self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.message, 0, wx.EXPAND)
        self.sizer.Add(self.donotshowagain, 0, wx.ALIGN_CENTER)
        self.sizer.Add(self.okButton, 0)

        #self.panel.SetSizer(self.sizer)
        #self.sizer.Fit(self)
        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

