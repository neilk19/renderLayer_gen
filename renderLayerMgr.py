import maya.app.renderSetup.model.override as override
import maya.app.renderSetup.model.renderSetup as renderSetup
import maya.app.renderSetup.model.renderLayer as renderLayer
from functools import partial
import maya.cmds as cmds
from PySide2 import QtWidgets
from PySide2 import QtCore
from PySide2 import QtGui
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui

def get_maya_window():
    main_win_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_win_ptr), QtWidgets.QWidget)

# Main
def create_layer():
    r1 = RenderLayerMgr()
    if r1.validation_chk() == True:
        for obj in r1.get_obj_transform_name():
            render_layer = r1.create_render_layer(obj)
            ren_layer_name = render_layer.name()
            r1.set_current_render_layer(ren_layer_name)
            objColl1 = r1.create_collection(render_layer, 'ObjectCollection_1')
            r1.add_obj_to_collection(obj=obj)
            # cmds.select(cl=True)
            objColl2 = r1.create_collection(render_layer, 'ObjectCollection_2')
            r1.add_obj_to_collection(obj=obj, selected=True)
            shapeColl = r1.create_collection(objColl2, 'ShapeCollection', pattern='*', filterType=2)
            r1.create_visibility_absoulte_override(shapeColl)

class GCProtector(object):
    """
    This class acts as a holder for a static class var in order to
    prevent Qt _widgets from being garbage-collected
    """
    # declare static class var
    widgets = []

# Custom label that switches between widgets on doubleClick mouse event
class SwitchLabel(QtWidgets.QLabel):
    def __init__(self, switch=None, parent=None):
        super(SwitchLabel, self).__init__(parent)
        self.switch = switch
        GCProtector.widgets.append(self)
    # When it's clicked, hide itself and show its buddy
    def mouseDoubleClickEvent(self, event):
        self.hide()
        self.switch.show()
        self.switch.setFocus(QtCore.Qt.MouseFocusReason)

# Custom button class
class DoubleClickEditButton(QtWidgets.QPushButton):

    def __init__(self, parent=None):
        super(DoubleClickEditButton, self).__init__(parent)

        self.setContentsMargins(0, 0, 0, 0)
        self.setCheckable(True)
        self.setFixedSize(400, 35)  # Set minimum otherwise it will collapse the container
        self.setCheckable(True)

        self.setStyleSheet("""
            QPushButton {
                background-color: rgb(93, 93, 93);
                border-radius: 3px;
                border: none;
            }

            QPushButton:checked {
                background-color: rgb(82,133,166);
                border-radius: 3px;
            }
        """)

# Renderlayer Ui item class
class RenderItemButton(DoubleClickEditButton):

    layer_nme_label = SwitchLabel(parent=None)

    def __init__(self, renderlayerName='', isVisible=bool, isRenderable=bool,layerInstance=None, parent=None):
        super(RenderItemButton, self).__init__(parent)

        self.render_layer_name = renderlayerName
        self.is_visible = isVisible
        self.is_renderable = isRenderable
        self.layer_instance = layerInstance
        self.jobList = []
        self.win_parent = parent


        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.create_script_jobs()

    def create_widgets(self):

        # Line edit to rename render layer
        self.layer_nme_le = QtWidgets.QLineEdit()
        self.layer_nme_le.setStyleSheet("QLineEdit {background-color: rgb(93, 93, 93);\n border: none;}")
        self.layer_nme_le.setContentsMargins(15, 0, 0, 0)
        self.layer_nme_le.setFixedSize(150, 20)
        self.layer_nme_le.setHidden(True)
        self.installEventFilter(self.layer_nme_le)

        # QLabel to display render layer name
        self.layer_nme_label = SwitchLabel(self.layer_nme_le)
        self.layer_nme_label.setParent(self)
        self.layer_nme_label.setStyleSheet("QLabel {background-color: rgb(93, 93, 93);\n border: none;}")
        self.layer_nme_label.setContentsMargins(15, 0, 0, 0)
        self.layer_nme_label.setFixedSize(150, 25)
        self.layer_nme_label.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Toggle render layer 'visibility' button
        self.set_render_layer_vis_btn = QtWidgets.QPushButton()
        self.set_render_layer_vis_btn.setCheckable(True)
        self.set_render_layer_vis_btn.setFixedSize(20, 20)
        self.set_render_layer_vis_btn.setIcon(QtGui.QIcon(":RS_visible.png"))


        # Toggle render layer 'renderable' button
        self.set_render_layer_current_btn = QtWidgets.QPushButton()
        self.set_render_layer_current_btn.setCheckable(True)
        self.set_render_layer_current_btn.setFixedSize(20, 20)
        self.set_render_layer_current_btn.setIcon(QtGui.QIcon(":RS_render.png"))


        # Delete renderlayer button
        self.delete_layer_btn = QtWidgets.QPushButton()
        self.delete_layer_btn.setStyleSheet("""QPushButton {
                                                  background-color: rgb(100,100,100);
                                                  border-radius: 12px;
                                                  box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19);
                                                  }
                                                  QPushButton:pressed {
                                                  background-color: rgb(50,50,50);
                                                  }""")
        self.delete_layer_btn.setFixedSize(24, 24)
        self.delete_layer_btn.setIcon(QtGui.QIcon(":SP_MessageBoxCritical.png"))

        # Edit renderlater button
        self.edit_layer_btn = QtWidgets.QPushButton()
        self.edit_layer_btn.setStyleSheet("""QPushButton {
                                          background-color: rgb(100,100,100);
                                          border-radius: 12px;
                                          box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2), 0 6px 20px 0 rgba(0,0,0,0.19);
                                          }
                                    
                                          QPushButton:pressed {
                                          background-color: rgb(50,50,50);
                                          }""")

        self.edit_layer_btn.setFixedSize(24, 24)
        self.edit_layer_btn.setIcon(QtGui.QIcon(":pencilCursor.png"))

        self.update_values()

    def create_layouts(self):
        self.main = QtWidgets.QHBoxLayout(self)
        self.main.setContentsMargins(60, 0, 0, 0)

        # Layer Render and visibility Button Group
        self.btn_grp_layout = QtWidgets.QHBoxLayout()
        self.btn_grp_layout.addWidget(self.set_render_layer_vis_btn)
        self.btn_grp_layout.addWidget(self.set_render_layer_current_btn)
        self.btn_grp_layout.setContentsMargins(5, 1, 5, 0)

        self.grp_box_layout = QtWidgets.QGroupBox(self)
        self.grp_box_layout.setFixedSize(60, 30)
        self.grp_box_layout.move(5, 3)
        self.grp_box_layout.setStyleSheet("QGroupBox {background-color: rgb(40,40,60);"
                                          "border-style: groove;"
                                          "border-radius: 5px;"
                                          "}")
        self.grp_box_layout.setLayout(self.btn_grp_layout)

        # Layout for edit and delete button
        self.del_edit_btn = QtWidgets.QHBoxLayout()
        self.del_edit_btn.setContentsMargins(100, 0, 0, 0)
        # self.del_edit_btn.addWidget(self.edit_layer_btn)
        self.del_edit_btn.addWidget(self.delete_layer_btn)

        # Layer Name and Edit name widgets
        self.main.addWidget(self.layer_nme_label)
        self.main.addWidget(self.layer_nme_le)
        self.main.addLayout(self.del_edit_btn)

    def create_connections(self):
        self.layer_nme_le.editingFinished.connect(self.set_renLayer_name)
        self.set_render_layer_vis_btn.pressed.connect(self.set_renLayer_vis)
        self.set_render_layer_current_btn.pressed.connect(self.set_renLayer_renderable)
        self.delete_layer_btn.pressed.connect(self.delete_ren_layer)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonDblClick:
            pass
            # self.layer_nme_le.setFocus(QtCore.Qt.MouseFocusReason)

    def update_values(self):
        self.get_renLayer_vis()
        self.get_renLayer_renderable()
        self.get_renLayer_name()
        pass

    #  Get UI Attribute values
    def get_UI_renLayer_name(self):
        text = self.layer_nme_label.text()
        return text

    #  Get Attribute values
    def get_renLayer_name(self):
        name = self.layer_instance.name()

        if self.render_layer_name == name:
            self.layer_nme_label.setText(self.render_layer_name)
            self.layer_nme_le.setText(self.render_layer_name)
        else:
            self.layer_nme_label.setText(name)
            self.layer_nme_le.setText(name)

    def get_renLayer_vis(self):
        is_vis = self.layer_instance.isVisible()
        if self.is_visible == is_vis:
            self.set_render_layer_vis_btn.setChecked(is_vis)
        else:
            self.set_render_layer_vis_btn.setChecked(self.is_visible)

    def get_renLayer_renderable(self):
        is_ren = self.layer_instance.isRenderable()
        if self.is_renderable == is_ren:
            self.set_render_layer_current_btn.setChecked(self.is_renderable)
        else:
            self.set_render_layer_current_btn.setChecked(is_ren)

    #  Set Attribute values
    def set_renLayer_name(self):
        self.layer_nme_le.setHidden(True)
        self.line_edit_text = self.layer_nme_le.text()
        self.layer_nme_label.show()
        self.layer_nme_label.setText(self.line_edit_text)
        self.layer_instance.setName(self.line_edit_text)

    def set_renLayer_vis(self):
        cmds.editRenderLayerGlobals(currentRenderLayer='rs_{0}'.format(self.render_layer_name))

    def set_renLayer_renderable(self):
        if self.set_render_layer_current_btn.isChecked() == True:
           self.layer_instance.setRenderable(False)
        if self.set_render_layer_current_btn.isChecked() == False:
           self.layer_instance.setRenderable(True)

    def delete_ren_layer(self):
        renderLayer.delete(self.layer_instance)

    def create_script_jobs(self):
        self.kill_scriptJobs()
        nodeNameChange = cmds.scriptJob(nodeNameChanged=['rs_{0}'.format(self.render_layer_name), self.update_values])
        self.jobList.append(nodeNameChange)

    def kill_scriptJobs(self):
        for job_number in self.jobList:
            cmds.evalDeferred('if cmds.scriptJob(exists={0}): \t cmds.scriptJob(kill={0}, force=True)'.format(job_number))
        self.script_jobs = []

# Main Ui
class RenLayerManagerUI(QtWidgets.QDialog):

    WIN_TITLE = 'RenderLayerGen'

    def __init__(self, parent=get_maya_window()):
        super(RenLayerManagerUI, self).__init__(parent)

        self.rs_functions = RenderLayerMgr()

        self.setWindowTitle(self.WIN_TITLE)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        self.setMinimumHeight(250)
        self.setFixedWidth(430)
        self.setContentsMargins(0, 0, 0, 0)

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

        self.jobList = []
        self.ren_item_list = []
        self.render_setup = renderSetup.instance()

        self.show()

    def create_widgets(self):
        self.containter_wdg = QtWidgets.QWidget()

        self.tip_text_label = QtWidgets.QLabel("First select 'mesh' object(s) you want to isolate")
        self.tip_text_label.setFont(QtGui.QFont("Times", 7, QtGui.QFont.Bold))
        self.tip_text_label.setAlignment(QtCore.Qt.AlignHCenter)
        self.tip_text_label.setFixedHeight(15)

        self.create_ren_layer_btn = QtWidgets.QPushButton('Create render layer')
        self.create_ren_layer_btn.setFixedWidth(200)
        self.create_ren_layer_btn.setFixedHeight(30)
        self.create_ren_layer_btn.setStyleSheet("QPushButton {"
                                                "background-color: rgba(93, 120, 93);"
                                                "border-radius: 4px;}"

                                                "QPushButton:pressed {"
                                                "background-color: rgba(60, 60, 60);"
                                                "border-radius: 4px;}"
                                        
                                                "QPushButton:released {"
                                                "background-color: rgba(93, 120, 93);"
                                                "border-radius: 4px;}")


        self.defaultRenderLayer_btn = QtWidgets.QPushButton('Return to DefaultRenderLayer')
        self.defaultRenderLayer_btn.setFixedWidth(200)
        self.defaultRenderLayer_btn.setFixedHeight(30)
        self.defaultRenderLayer_btn.setStyleSheet("QPushButton: {"
                                                    "background-color: rgba(100, 100, 100);"
                                                    "border-radius: 4px;}"

                                                    "QPushButton:pressed {"
                                                    "background-color: rgba(100, 110, 110);"
                                                    "border-radius: 4px;}")

    def create_layouts(self):
        self.layer_selection_btn_group = QtWidgets.QButtonGroup()
        self.layer_vis_btn_group = QtWidgets.QButtonGroup()

        self.create_btn_layout = QtWidgets.QHBoxLayout()
        self.create_btn_layout.setContentsMargins(0,0,0,0)
        self.create_btn_layout.setAlignment(QtCore.Qt.AlignHCenter)
        self.create_btn_layout.addWidget(self.create_ren_layer_btn)
        self.create_btn_layout.addWidget(self.defaultRenderLayer_btn)

        self.ren_layer_list_layout = QtWidgets.QVBoxLayout(self.containter_wdg)
        self.ren_layer_list_layout.setContentsMargins(10, 10, 10, 10)
        self.ren_layer_list_layout.setSpacing(3)
        self.ren_layer_list_layout.setAlignment(QtCore.Qt.AlignTop)

        self.light_list_scroll = QtWidgets.QScrollArea()
        self.light_list_scroll.setWidgetResizable(True)
        self.light_list_scroll.setWidget(self.containter_wdg)

        self.mainlayout = QtWidgets.QVBoxLayout(self)
        self.mainlayout.setContentsMargins(0, 10, 0, 0)
        self.mainlayout.addWidget(self.tip_text_label)
        self.mainlayout.addLayout(self.create_btn_layout)
        self.mainlayout.addWidget(self.light_list_scroll)

    def create_connections(self):
        self.create_ren_layer_btn.pressed.connect(create_layer)
        self.defaultRenderLayer_btn.pressed.connect(self.set_default)

    def create_scriptJobs(self):
        self.kill_scriptJobs()
        job = cmds.scriptJob(event=('renderLayerManagerChange', self.refresh_values))
        job1 = cmds.scriptJob(event=('renderLayerChange', self.refresh_values))
        self.jobList.append(job)
        self.jobList.append(job1)

    def kill_scriptJobs(self):
        for job_number in self.jobList:
            cmds.evalDeferred(
                'if cmds.scriptJob(exists={0}): \t cmds.scriptJob(kill={0}, force=True)'.format(job_number))
        self.script_jobs = []

    def is_more_than_one_obj(self):
        ren_manager_inst = RenderLayerMgr()
        obj_list = ren_manager_inst.get_obj_transform_name()
        return obj_list

    def refresh_values(self):
        self.clear_items()
        self.render_layers = self.render_setup.getRenderLayers()
        for render_layer in self.render_layers:
            render_layer_name = render_layer.name()  # Without "rs_" prefix
            is_renderable = render_layer.isRenderable()
            is_visible = render_layer.isVisible()

            self.render_layer_item = RenderItemButton(render_layer_name,
                                                      is_visible,
                                                      is_renderable,
                                                      render_layer,
                                                     parent=self)

            self.ren_item_list.append(self.render_layer_item)
            self.layer_selection_btn_group.addButton(self.render_layer_item)
            self.layer_vis_btn_group.addButton(self.render_layer_item.set_render_layer_vis_btn)
            self.ren_layer_list_layout.addWidget(self.render_layer_item)

    def clear_items(self):
        for item in self.ren_item_list:
            item.kill_scriptJobs()
            self.ren_item_list = []

        # Clearing the ligh list
        while self.ren_layer_list_layout.count() > 0:
            light_item = self.ren_layer_list_layout.takeAt(0)
            if light_item.widget():
                light_item.widget().deleteLater()

    def get_renlayer_list(self):
        render_layer_names = self.render_setup.getRenderLayers()
        return render_layer_names

##########################################
#   Default Render Layer functions
##########################################

    def set_default(self):
        self.set_visible_default_render_layer()
        self.set_renderable_default_render_layer()

    def get_default_render_layer(self):
        ren_instance = renderSetup.instance()
        def_renLayer = ren_instance.getDefaultRenderLayer()
        return def_renLayer

    def is_visible_defualt_render_layer(self):
        instance = self.get_default_render_layer()
        is_vis = instance.isVisible()
        return is_vis

    def is_renderable_default_render_layer(self):
        instance = self.get_default_render_layer()
        is_ren = instance.isRenderable()
        return is_ren

    def set_visible_default_render_layer(self):
        cmds.editRenderLayerGlobals(currentRenderLayer='defaultRenderLayer')

    def set_renderable_default_render_layer(self):
        instance = self.get_default_render_layer()
        set_ren = instance.setRenderable(True)

# ##########################################
#   Event functions
##########################################

    def showEvent(self, event):
        self.create_scriptJobs()
        self.refresh_values()

    def closeEvent(self, event):
        self.clear_items()
        self.kill_scriptJobs()
        self.close()
        self.deleteLater()

# Main class
class RenderLayerMgr(object):
    def __init__(self):
        self.ren_lyr_obj = renderSetup.instance()  # RenderSetup Instance

# Validates some requisites before executing main function
    def validation_chk(self):
        pixMap = QtGui.QPixmap()
        pixMap.load(":SP_MessageBoxWarning.png")

        warning_msg_bx = QtWidgets.QMessageBox(get_maya_window())

        win = QtWidgets.QDialog(parent=get_maya_window())
        win.move(QtWidgets.QApplication.desktop().screen().rect().center())

        #-----------------------------------------------------------
        # Validate whether single at least one object is selected
        #-----------------------------------------------------------
        sel_lst = cmds.ls(sl=True, dag=True, o=True)
        if not sel_lst:
            warning_msg_bx.setWindowTitle('ERROR')
            warning_msg_bx.setText("Choose at least one 'mesh' object")
            warning_msg_bx.setIconPixmap(pixMap)
            warning_msg_bx.show()
            raise Exception("No SINGLE Object Selected")

        # -----------------------------------------------------------
        # Validate whether selected object is group (Groups are not yet supported)
        # -----------------------------------------------------------
        sel = cmds.ls(sl=True, dag=True, type='transform')
        for item in sel:
            child = cmds.listRelatives(item, c=True)[0]
            object_type = cmds.objectType(child)
            if object_type == 'transform':
                warning_msg_bx.setWindowTitle('TypeError')
                warning_msg_bx.setText("Only 'mesh' supported, 'group' recieved")
                warning_msg_bx.setIconPixmap(pixMap)
                warning_msg_bx.show()
                raise TypeError("Only mesh type transform supported")

        # -----------------------------------------------------------
        # Validate that the selected object is a mesh
        # -----------------------------------------------------------
        for item in sel:
            child = cmds.listRelatives(item, c=True)[0]
            object_type = cmds.objectType(child)
            if object_type != 'mesh':
                warning_msg_bx.setWindowTitle('TypeError')
                warning_msg_bx.setText('Only "mesh" supported, "{0}" type recieved'.format(object_type))
                warning_msg_bx.setIconPixmap(pixMap)
                warning_msg_bx.show()
                raise TypeError("Only mesh type transform supported")
                return False
        else:
            return True

# Creates a empty render layer
    def create_render_layer(self, name=''):
        return self.ren_lyr_obj.createRenderLayer(name)

# Creates collection with provided settings
    def create_collection(self, instance, name, pattern='', filterType=1):
        self.collection = instance.createCollection(name)
        get_selector = self.collection.getSelector()
        get_selector.setPattern(pattern)
        get_selector.setFilterType(filterType)
        return self.collection

# Returns --list-- of object(s) in scene
    def get_scene_objects(self, remove=None):
        sel = cmds.ls(dag=True, type='transform')
        shapes = cmds.listRelatives(sel, type='mesh')
        transform = cmds.listRelatives(shapes, p=True)
        if remove:
            for item in transform :
                if item == remove:
                    transform.remove(item)
                    return transform
        else:
            return transform

# Returns --list-- of selected 'DAG' objects in the scene
    def selected_object(self):
        sel = cmds.ls(sl=True, dag=True, o=True)
        return sel

# Creates a 'visibility' override on the shape nodes
    def create_visibility_absoulte_override(self, collection, value=False):
        '''
        :param collection: (obj) passes collection instance
        :param value: (bool, int, str) Takes attribute value
        :return:
        '''

        # Create proxy object to get the shape override attribute
        pxyObject = cmds.polySphere()
        shape = cmds.listRelatives(pxyObject, s=True)[0]

        oOverride = collection.createOverride('Visibility Override', override.AbsOverride.kTypeId)
        plug = '{}.primaryVisibility'.format(shape)
        oOverride.setAttributeName(plug)
        oOverride.finalize(plug)
        oOverride.setAttrValue(value)

        cmds.delete(pxyObject)

# Populating collection with object
    def add_obj_to_collection(self, obj=None, selected=False):
        item = obj
        scene = self.get_scene_objects(remove=item)
        print(item)
        if not selected:
            self.collection.getSelector().staticSelection.set(self.get_scene_objects())
        else:
            self.collection.getSelector().staticSelection.set(self.get_scene_objects(remove=item))

# Get object's transform name
    def get_obj_transform_name(self):
        obj = cmds.ls(sl=True)
        return obj

# REDUNDENT FUNCTION
    def get_attrOvr_value(self, node, ovr):
        self.ren_lyr_obj.availableOverrides(node, ovr)

# REDUNDENT FUNCTION
    def get_obj_shape(self, objs):  # Returns a shape Node or --list-- of shape nodes
        '''
        :param objs: if is a --list-- return list of shapes
        '''
        if isinstance(objs, list):
            shape_list = []
            for item in objs:
                shape = cmds.listRelatives(item, shapes=True)
                if not shape:
                    continue
                shape_list.append(shape[0])
            return shape_list
        else:
            shape = cmds.listRelatives(objs, shapes=True)
            return shape

# Returns a shape Node or --list-- of transform nodes
    def get_obj_transform(self, objs):
        if isinstance(objs, list):
            transform_list = []
            for item in objs:
                transform = cmds.listRelatives(item, shapes=True)
                if not transform:
                    continue
                transform_list.append(transform[0])
            return transform_list
        else:
            transform = cmds.listRelatives(objs, shapes=True)
            return transform

# Returns a --list-- with names of render Layers.
    def get_render_layer_names(self):
        render_layer_names = cmds.renderSetup(q=True, renderLayers=True)
        return render_layer_names

# Set provided render layer as current Layer
    def set_current_render_layer(self, renLayer):
        cmds.editRenderLayerGlobals(currentRenderLayer='rs_{0}'.format(renLayer))

try:
    ren_mgr.close()
    ren_mgr.deleteLater()
except:
    pass
ren_mgr = RenLayerManagerUI()




