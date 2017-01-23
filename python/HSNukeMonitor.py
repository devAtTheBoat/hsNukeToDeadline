import nuke
import os
import nukescripts

class HSNukeMonitor(nukescripts.PythonPanel):
    def __init__(self):
        nukescripts.PythonPanel.__init__(self, 'HoveringSombrero Monitor for Nuke', 'com.hoveringsombrero.monitor')


        self.hsSettings = {}

        hsSettings = os.environ.get("HS_SETTINGS_KEYS").split(":")

        for setting in hsSettings:
            self.hsSettings[setting] = os.environ.get(setting)

        for key, value in self.hsSettings.iteritems():
            newKnob = nuke.String_Knob(key, key)
            self.addKnob( newKnob )
            newKnob.setValue( value )
            newKnob.setEnabled( False )


        self.separator1 = nuke.Text_Knob( "separator1", "" )
        self.addKnob( self.separator1 )

        self.projectSettings = {}

        hsProjectSettings = os.environ.get("HS_PROJECT_SETTINGS_KEYS").split(":")

        for setting in hsProjectSettings:
            self.projectSettings[setting] = os.environ.get(setting)

        for key, value in self.projectSettings.iteritems():
            newKnob = nuke.String_Knob(key, key)
            self.addKnob( newKnob )
            newKnob.setValue( value )
            newKnob.setEnabled( False )
