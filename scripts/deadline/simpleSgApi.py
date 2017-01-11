from shotgun_api3 import Shotgun

class simpleSgApi:
    sg_site = 'https://hovering-sombrero.shotgunstudio.com'
    sg_script_name = 'deadline_integration'
    sg_script_key = '02e9a898937ba3ffdb0da35b4a43e1eb5f1353c758132708db74336c24a9bd4b'

    def __init__(self):
        print 'Shotgun API starting...'
        self.sg = Shotgun(simpleSgApi.sg_site, simpleSgApi.sg_script_name, simpleSgApi.sg_script_key)

    def connect(self, user):
        self.user = user
        return self.user

    def getTasks(self):
        filters = [['task_assignees.HumanUser.login', 'is', self.user],
         ['sg_status_list', 'is_not', 'fin'],
         ['sg_status_list', 'is_not', 'cmpt'],
         ['sg_status_list', 'is_not', 'wtg'],
         ['sg_status_list', 'is_not', 'omt']]
        fields = ['content',
         'entity',
         'step',
         'project']
        tasks = self.sg.find('Task', filters, fields)
        return sorted(tasks)

    def getLatestVersion(self, task):
        filters = [['sg_task', 'is', {'type': 'Task',
           'id': task['id']}]]
        fields = ['id', 'code']
        try:
            latestVersion = self.sg.find('Version', filters, fields, order=[{'column': 'updated_at',
              'direction': 'desc'}])[0]
            return latestVersion
        except:
            return None
