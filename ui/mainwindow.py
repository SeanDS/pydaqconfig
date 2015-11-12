from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
import glob
import os.path
import shutil
import time
import subprocess

from daq import daqmodel, utils
from channeltreemodel import ChannelTreeModel, ComboDelegate

class MainWindow(QMainWindow):
    ENV_CDS_DAQ_CHANS = 'PYDAQCONFIG_CHAN_DIR'
    ENV_POST_SAVE_CMD = 'PYDAQCONFIG_POST_SAVE_CMD'

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        uic.loadUi('ui/mainwindow.ui', self)
        
        self._models = []
        self._models_changed = []

        self._tvmodel = ChannelTreeModel(self._models, parent=self)
        self.twChannels.setModel(self._tvmodel)
        self.twChannels.expanded.connect(self.resize_columns)
        self.load_models()

        datarates = [2**n for n in range(1,17)]
        d_datarates = zip(map(str, datarates), datarates)
        self.twChannels.setItemDelegateForColumn(2, ComboDelegate(d_datarates, self.twChannels))
        self.twChannels.model().dataChanged.connect(self.data_changed)

    def launch_post_save_cmd(self, updated_files):
        env = QProcessEnvironment.systemEnvironment()
        print 'Calling post-save command (in {0})...'.format(self.ENV_POST_SAVE_CMD) ,
        if env.contains(self.ENV_POST_SAVE_CMD):
            cmd = str(env.value(self.ENV_POST_SAVE_CMD))
            #TODO: maybe use check_output() and then display a log window
            try:
                subprocess.check_call([cmd]+updated_files)
                print 'done.'
            except subprocess.CalledProcessError as e:
                QMessageBox.warning(self, 'Error in post-save command',
                    'There has been an error while executing the post-save command. The returned error code was {0}. Please check the output in the command-line terminal to see what went wrong.'.format(e.returncode))
                return False
        else:
            print 'none set.'

        return True

    def get_ini_directory(self):
        models = []
        env = QProcessEnvironment.systemEnvironment()
        if env.contains(self.ENV_CDS_DAQ_CHANS):
            directory = str(env.value(self.ENV_CDS_DAQ_CHANS))
            return os.path.abspath(os.path.expanduser(directory))
        else:
            return None

    def load_models_from_files(self):
        #TODO: automatically load these, based on ENV variable or so
        models = []
        directory = self.get_ini_directory()
        if not directory:
            QMessageBox.critical(self, 'Unable to locate DAQ channels', 
                ('Please set the environmental variable {0} to '+
                'the directory which contains the DAQ .ini files.').format(
                    self.ENV_CDS_DAQ_CHANS))
        else:
            for fn in glob.glob(directory+'/*.ini'):
                print 'Loading {0}...'.format(fn)
                ini = open(fn, 'rb')
                dm = daqmodel.DAQModel.from_ini(utils.get_model_name(fn), ini)
                if dm:
                    models.append(dm)
        return models

    def load_models(self):
        self._models = self.load_models_from_files()
        self._models_changed = dict([(m.name, False) for m in self._models])
        self.twChannels.model().populate(self._models)

        self.update_save_state()
        self.set_statusbar_timestamp()

    def save_model(self, model):
        directory = self.get_ini_directory()
        basename = os.path.join(directory, model.name+'.ini')
        new_ini = basename + '.new'
        bak_ini = basename + '.bak'
        print 'Saving {0} to {1}...'.format(model.name, basename) ,
        with open(new_ini, 'wb') as fp:
            model.to_ini(fp)
            shutil.copy(basename, bak_ini)
            shutil.move(new_ini, basename)
            print 'done.'
        return basename

    def has_changes(self):
        return any(self._models_changed.itervalues())

    def find_channel(self, name):
        for model in self._models:
            chan = model.find_channel(name)
            if chan:
                return chan
        return None

    def set_statusbar_timestamp(self):
        now = time.strftime('%d/%m/%Y at %H:%M:%S UTC', time.gmtime())
        self.stbStatus.showMessage('Channels loaded on {0}.'.format(now))
    
    def update_save_state(self):
        title = 'pyDAQConfig'
        changed = self.has_changes()
        self.btnSave.setEnabled(changed)
        if changed:
            title += ' (edited)'
        self.setWindowTitle(title)
    
    @pyqtSlot()
    def resize_columns(self):
        for col in range(self.twChannels.model().columnCount(None)):
            self.twChannels.resizeColumnToContents(col)

    @pyqtSlot(QModelIndex, QModelIndex)
    def data_changed(self, left, right):
        model = str(left.parent().data().toString())
        self._models_changed[model] = True
        self.update_save_state()

    @pyqtSlot()
    def on_btnReload_clicked(self):
        if self.has_changes():
            retval = QMessageBox.question(self, 'Discard Changes?',
                'You have unsaved changes. Do you want to discard them and reload the channels?',
                QMessageBox.Yes | QMessageBox.No)
            if retval == QMessageBox.Yes:
                self.load_models()
        
    @pyqtSlot()
    def on_btnSave_clicked(self):
        updated_files = []
        for model in self._models:
            if self._models_changed[model.name]:
                updated_files.append(self.save_model(model))
                self._models_changed[model.name] = False
        if updated_files:
            if self.launch_post_save_cmd(updated_files):
                QMessageBox.information(self, 'DAQ Channels Saved',
                    'The DAQ channel files have been saved successfully.')
            self.update_save_state()
            self.set_statusbar_timestamp()

    @pyqtSlot()
    def on_btnChannelSets_clicked(self):
        dlg = ChannelSetsDialog(self)
        if dlg.exec_() == QDialog.Accepted:
            print "accepted"
        else:
            print "rejected"

