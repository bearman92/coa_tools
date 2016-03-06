'''
Copyright (C) 2015 Andreas Esau
andreasesau@gmail.com

Created by Andreas Esau

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

bl_info = {
    "name": "Cutout Animation Tools",
    "description": "This Addon provides a Toolset for a 2D Animation Workflow.",
    "author": "Andreas Esau",
    "version": (0, 1, 0, "Alpha"),
    "blender": (2, 75, 0),
    "location": "View 3D > Tools > Cutout Animation Tools",
    "warning": "This addon is still in development.",
    "wiki_url": "",
    "category": "Ndee Tools" }
    
import bpy
import bpy_extras
import bpy_extras.view3d_utils
from math import radians
import mathutils
from mathutils import Vector, Matrix, Quaternion
import math
import bmesh
from bpy.props import FloatProperty, IntProperty, BoolProperty, StringProperty, CollectionProperty, FloatVectorProperty, EnumProperty, IntVectorProperty
import os
from bpy_extras.io_utils import ExportHelper, ImportHelper
import json
from bpy.app.handlers import persistent
from . functions import *
#from . import preview_collections

bone_layers = []
armature_mode = None
armature_select = False
tmp_active_object = None


class AnimationCollections(bpy.types.PropertyGroup):
    def set_frame_start(self,context):
        bpy.context.scene.frame_start = self.frame_start
    def set_frame_end(self,context):
        bpy.context.scene.frame_end = self.frame_end
    
    def check_name(self,context):
        sprite_object = get_sprite_object(context.active_object)
        
        if self.name_old != "" and self.name_change_to != self.name:
            name_array = []
            for item in sprite_object.coa_anim_collections:
                name_array.append(item.name_old)
            self.name_change_to = check_name(name_array,self.name)
            self.name = self.name_change_to 
        
        for child in get_children(context,sprite_object,ob_list=[]):
            action_name = self.name_old + "_" + child.name
            action_name_new = self.name + "_" + child.name
            if action_name in bpy.data.actions:
                action = bpy.data.actions[action_name]
                action.name = action_name_new
        self.name_old = self.name
    
    name = StringProperty(update=check_name)
    name_change_to = StringProperty()
    name_old = StringProperty()
    action_collection = BoolProperty(default=False)
    frame_start = IntProperty(default=0 ,update=set_frame_start)
    frame_end = IntProperty(default=250 ,update=set_frame_end)
        

class CutoutAnimationInfo(bpy.types.Panel):
    bl_idname = "cutout_animation_social"
    bl_label = "Cutout Animation Social"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Cutout Animation"
    
    @classmethod
    def poll(cls, context):
        if get_addon_prefs(context).show_donate_icon:
            return context
    
    def draw(self, context):
        
        
        layout = self.layout
        
        row = layout.row()
        row.alignment = "CENTER"
        
        pcoll = preview_collections["main"]
        donate_icon = pcoll["donate_icon"]
        twitter_icon = pcoll["twitter_icon"]
        row.operator("coa_operator.coa_donate",text="Show Your Love",icon_value=donate_icon.icon_id,emboss=True)
        row = layout.row()
        row.alignment = "CENTER"
        row.scale_x = 1.75
        op = row.operator("coa_operator.coa_tweet",text="Tweet",icon_value=twitter_icon.icon_id,emboss=True)
        op.link = "https://www.youtube.com/ndee85"
        op.text = "Check out CutoutAnimation Tools Addon for Blender by Andreas Esau."
        op.hashtags = "b3d,coatools"
        op.via = "ndee85"

class AddKeyframe(bpy.types.Operator):
    bl_idname = "my_operator.add_keyframe"
    bl_label = "Add Keyframe"
    bl_description = "Add Keyframe"
    bl_options = {"REGISTER"}
    
    prop_name = StringProperty()
    add_keyframe = BoolProperty(default=True)
    
    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        sprite = context.active_object
        sprite_object = get_sprite_object(sprite)
        if self.add_keyframe:
            if sprite.animation_data != None and sprite.animation_data.action != None:
                sprite.keyframe_insert(self.prop_name)
            else:
                create_action(context)
                sprite.keyframe_insert(self.prop_name)
            self.report({'INFO'},str("Keyframe added at frame "+str(context.scene.frame_current)+"."))    
        else:
            if sprite.animation_data != None and sprite.animation_data.action != None:
                sprite.keyframe_delete(self.prop_name)
                
                collection = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index]
                action_name = collection.name + "_" +sprite.name
                if action_name in bpy.data.actions:
                    action = bpy.data.actions[action_name]
                    if len(action.fcurves) == 0:
                        action.use_fake_user = False
                        action.user_clear()   
                self.report({'INFO'},str("Keyframe deleted at frame "+str(context.scene.frame_current)+"."))
                set_action(context)
            else:
                self.report({'WARNING'},str("Sprite has no Animation assigned."))       
        return {"FINISHED"}
        
    
class CutoutAnimationObjectProperties(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Object Properties"
    bl_category = "Cutout Animation"
    
    @classmethod
    def poll(cls, context):
        if get_sprite_object(context.active_object) != None:
            return (context.active_object)
    
    def hide_bone(self,context):
        self.hide = self.coa_hide
    
    def hide_select_bone(self,context):
        self.hide_select = self.coa_hide_select
    
    def hide(self,context):
        if self.coa_hide:
            if context.scene.objects.active == self:
                context.scene.objects.active = self.parent
        self.hide = self.coa_hide
    def hide_select(self,context):
        if self.coa_hide_select:
            self.select = False
            if context.scene.objects.active == self:
                context.scene.objects.active = self.parent
        self.hide_select = self.coa_hide_select
    
    def update_uv(self,context):
        if self.coa_sprite_frame >= (self.coa_tiles_x * self.coa_tiles_y):
            self.coa_sprite_frame = (self.coa_tiles_x * self.coa_tiles_y) - 1
        update_uv(context,context.active_object)
    
    def update_verts(self,context):
        update_uv(context,context.active_object)
        update_verts(context,context.active_object)
        
    def set_alpha(self,context):
        set_alpha(self,context)
            
        
    bpy.types.Object.coa_dimensions_old = FloatVectorProperty()
    bpy.types.Object.coa_sprite_dimension = FloatVectorProperty()
    bpy.types.Object.coa_tiles_x = IntProperty(description="X Tileset",default = 1,min=1,update=update_verts)
    bpy.types.Object.coa_tiles_y = IntProperty(description="Y Tileset",default = 1,min=1,update=update_verts)
    bpy.types.Object.coa_sprite_frame = IntProperty(description="Frame",default = 0,min=0,update=update_uv)
    bpy.types.Object.coa_z_value = IntProperty(description="Z Depth",default=0)
    bpy.types.Object.coa_alpha = FloatProperty(default=1.0,min=0.0,max=1.0,update=set_alpha)
    bpy.types.Object.coa_show_bones = BoolProperty()
    bpy.types.Object.coa_filter_names = StringProperty()
    bpy.types.Object.coa_favorite = BoolProperty()
    bpy.types.Bone.coa_favorite = BoolProperty()
    bpy.types.Object.coa_edit_weights = BoolProperty(default=False)
    bpy.types.Object.coa_edit_armature = BoolProperty(default=False)
    bpy.types.Object.coa_edit_mesh = BoolProperty(default=False)
    bpy.types.Object.coa_hide = BoolProperty(default=False,update=hide)
    bpy.types.Object.coa_hide_select = BoolProperty(default=False,update=hide_select)
    bpy.types.Object.coa_data_path = StringProperty()
    bpy.types.Object.coa_show_children = BoolProperty(default=True)
    bpy.types.Bone.coa_draw_bone = BoolProperty(default=False)
    bpy.types.Bone.coa_z_value = IntProperty(description="Z Depth",default=0)
    bpy.types.Bone.coa_data_path = StringProperty()
    bpy.types.Bone.coa_hide_select = BoolProperty(default=False, update=hide_select_bone)
    bpy.types.Bone.coa_hide = BoolProperty(default=False,update=hide_bone)
    bpy.types.Object.coa_show_export_box = BoolProperty()
    
    
    bpy.types.WindowManager.coa_running_modal = BoolProperty(default=False)
    
                
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        scene = context.scene
        
        if sprite_object != None:
            if len(sprite_object.children) > 0:
                display_children(self,context,sprite_object)
            
            row = layout.row(align=True)
            row.label(text="",icon="OBJECT_DATA")
            row.separator()
            row.prop(obj,"name",text="")
            if obj.type == "ARMATURE":
                row = layout.row(align=True)
                if context.active_bone != None:
                    row.label(text="", icon="BONE_DATA")
                    row.separator()
                    row.prop(context.active_bone,'name',text="")
                    if context.active_object.mode != "EDIT":
                        box = layout.box()
                        row = box.row(align=True)
                        if sprite_object.coa_show_export_box:
                            row.prop(sprite_object,"coa_show_export_box",text="Json Export Properties",icon="TRIA_DOWN",emboss=False)
                            row = box.row(align=True)
                            row.prop(context.active_bone,"coa_draw_bone",text="Draw Bone on export")
                            row = box.row(align=True)
                        else:
                            row.prop(sprite_object,"coa_show_export_box",text="Json Export Properties",icon="TRIA_RIGHT",emboss=False)    
            
            if obj != None and obj.type == "MESH":
                row = layout.row(align=True)
                row.label(text="Sprite Properties:")
            if obj != None and obj.type == "MESH" and len(obj.data.vertices) == 4:
                
                row = layout.row(align=True)
                text = str(obj.coa_tiles_x * obj.coa_tiles_y) + " Frame(s) total"
                row.label(text=text)
                    
                row = layout.row(align=True)
                row.prop(obj,'coa_tiles_x',text="Tiles X")
                row.prop(obj,'coa_tiles_y',text="Tiles Y")
                
                row = layout.row(align=True)
                row.prop(obj,'coa_sprite_frame',text="Frame Index",icon="UV_FACESEL")
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                op.prop_name = "coa_sprite_frame"
                op.add_keyframe = True
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                op.prop_name = "coa_sprite_frame"
                op.add_keyframe = False
            if obj != None and obj.type == "MESH":
                row = layout.row(align=True)
                row.prop(obj,'coa_alpha',text="Alpha",icon="TEXTURE")
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                op.prop_name = "coa_alpha"
                op.add_keyframe = True
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                op.prop_name = "coa_alpha"
                op.add_keyframe = False
                
                row = layout.row(align=True)
                row.prop(obj,'coa_z_value',text="Z Depth")
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE2")
                op.prop_name = "coa_z_value"
                op.add_keyframe = True
                op = row.operator("my_operator.add_keyframe",text="",icon="SPACE3")
                op.prop_name = "coa_z_value"
                op.add_keyframe = False
                
                                
######################################################################################################################################### Cutout Animation Tools Panel
class CutoutAnimationTools(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_label = "Cutout Animation Tools"
    bl_category = "Cutout Animation"
    
    def snapping(self,context):
        if bpy.context.scene.coa_surface_snap:
            bpy.context.scene.tool_settings.use_snap = True
            bpy.context.scene.tool_settings.snap_element = 'FACE'
        else:
            bpy.context.scene.tool_settings.use_snap = False
    
    def lock_view(self,context):
        if bpy.data.scenes[0].coa_lock_view == False:
            set_view("PERSP",set_current_screen=True)
            set_middle_mouse_move(False)

    
        
                    
    bpy.types.Scene.coa_distance = FloatProperty(description="Set the asset distance for each Paint Stroke",default = 1.0,min=-.0, max=30.0)
    bpy.types.Scene.coa_detail = FloatProperty(description="Detail",default = .3,min=0,max=1.0)
    bpy.types.Scene.coa_snap_distance = FloatProperty(description="Snap Distance",default = 0.01,min=0)
    bpy.types.Scene.coa_surface_snap = BoolProperty(default=False,description="Snap Vertices on Surface",update=snapping)
    bpy.types.Scene.coa_automerge = BoolProperty(default=False)
    bpy.types.Scene.coa_distance_constraint = BoolProperty(default=True,description="Constraint Distance to Viewport")
    bpy.types.Scene.coa_lock_to_bounds = BoolProperty(default=True,description="Lock Cursor to Object Bounds")
    bpy.types.Scene.coa_lock_view = BoolProperty(default=False, description="Locks the View to an Orthographic Front View",update=lock_view)
    
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        scene = context.scene    
        
        row = layout.row(align=True)
        if scene.coa_lock_view == False:
            row.operator("scene.coa_lock_view",text="3D View",icon="MESH_CUBE")
        else:
            row.prop(bpy.data.scenes[0],"coa_lock_view",text="2D View",icon="MATPLANE")
        
        row = layout.row(align=True)
        row.label(text="General Operator:")
        
        row = layout.row(align=True)
        row.operator("wm.coa_create_ortho_cam",text="Create Ortho Camera", icon="OUTLINER_DATA_CAMERA")
        
        if context.active_object == None or (context.active_object != None and context.active_object.mode not in ["EDIT","WEIGHT_PAINT"]):
            row = layout.row(align=True)
            row.operator("wm.coa_create_sprite_object",text="Create new Sprite Object",icon="TEXTURE_DATA")
        
        
        if obj != None and obj.type == "CAMERA":
            row = layout.row(align=True)
            op = row.operator("wm.coa_create_ortho_cam",text="Reset Camera Resolution",icon="OUTLINER_DATA_CAMERA")
            op.create = False
        
        if context.active_object != None and get_sprite_object(context.active_object) != None:
            if sprite_object.coa_edit_weights == False:
                if context.active_object.mode != "EDIT":
                    row = layout.row(align=True)
                    row.operator("import.coa_import_sprites",text="Import Sprites",icon="IMASEL")
                    
                    row = layout.row()
                    row.operator("object.export_to_json",text="Export Json",icon="EXPORT",emboss=True)
                    
                row = layout.row(align=True)
                row.label(text="Edit Operator:")
                
                row = layout.row(align=True)
                if sprite_object.coa_edit_mesh == False and sprite_object.coa_edit_armature == False and sprite_object.coa_edit_weights == False and not(obj.type == "MESH" and obj.mode=="EDIT"):  
                    row.operator("scene.coa_quick_armature",text="Edit Armature",icon="ARMATURE_DATA")
                elif sprite_object.coa_edit_armature:
                    row.prop(sprite_object,"coa_edit_armature", text="Finish Edit Armature",icon="ARMATURE_DATA")
                if context.active_object != None and context.active_object.mode == "POSE":
                    row = layout.row(align=True)
                    row.label(text="Bone Constraint Operator:")
                    row = layout.row(align=True)
                    row.operator("object.coa_set_ik",text="Create IK Bone",icon="CONSTRAINT_BONE")
                    row = layout.row(align=True)
                    row.operator("bone.coa_set_stretch_bone",text="Create Stretch Bone",icon="CONSTRAINT_BONE")

            if context.active_object.type == "MESH":
                if sprite_object.coa_edit_mesh == False and sprite_object.coa_edit_armature == False and sprite_object.coa_edit_weights == False:
                    row = layout.row(align=True)
                    row.operator("object.coa_edit_mesh",text="Edit Mesh",icon="GREASEPENCIL")
                elif sprite_object.coa_edit_mesh:
                    row = layout.row(align=True)
                    row.prop(sprite_object,"coa_edit_mesh", text="Finish Edit Mesh", toggle=True, icon="GREASEPENCIL")
            
                if sprite_object.coa_edit_mesh == False and sprite_object.coa_edit_armature == False and sprite_object.coa_edit_weights == False and not(obj.type == "MESH" and obj.mode=="EDIT") and (sprite_object) != None:
                    row = layout.row(align=True)
                    row.operator("object.coa_edit_weights",text="Edit Weights",icon="MOD_VERTEX_WEIGHT")
                elif sprite_object.coa_edit_weights:
                    row = layout.row(align=True)
                    row.prop(sprite_object,"coa_edit_weights", text="Finish Edit Weights", toggle=True, icon="MOD_VERTEX_WEIGHT")
                    
                    col = layout.split().column()
                    tool_settings = scene.tool_settings
                    brush_data = tool_settings.weight_paint
                    
                    col.template_ID_preview(brush_data, "brush", new="brush.add", rows=3, cols=8)
                    col = layout.column(align=True)
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings,"weight")
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings,"size")
                    row.prop(tool_settings.unified_paint_settings,"use_pressure_size",text="")
                    row = col.row(align=True)
                    row.prop(tool_settings.unified_paint_settings,"strength")
                    row.prop(tool_settings.unified_paint_settings,"use_pressure_strength",text="")
                    row = col.row(align=True)
                    row.prop(tool_settings,"use_auto_normalize",text="Auto Normalize")
                    
        if context.active_object != None and context.active_object.mode == "EDIT" and context.active_object.type == "MESH" and sprite_object.coa_edit_mesh:
            row = layout.row(align=True)
            row.label(text="Mesh Tools:")
            
            row = layout.row(align=True)
            operator = row.operator("object.coa_fill",text="Normal Fill",icon="OUTLINER_OB_SURFACE")
            operator.triangulate = False
            
            row = layout.row(align=True)
            operator = row.operator("object.coa_fill",text="Triangle Fill",icon="OUTLINER_OB_SURFACE")
            operator.triangulate = True
            
            col = layout.column(align=True)
            row2 = col.row(align=True)
            row2.prop(scene,'coa_snap_distance',text="Merge Distance")
            
            row2 = col.row(align=True)
            row2.prop(scene,'coa_distance',text="Stroke Distance")
            row2.row(align=True).prop(scene,'coa_distance_constraint',text="",icon="CONSTRAINT")
            
            row2 = col.row(align=True)
            row2.prop(scene,'coa_surface_snap',text="Snap Vertices",icon="SNAP_SURFACE")
            
            row2 = col.row(align=True)
            row2.prop(scene,'coa_automerge',text="Merge Vertices",toggle=True,icon="AUTOMERGE_ON")
            
            row2 = col.row(align=True)
            if scene.coa_lock_to_bounds:
                row2.prop(scene,"coa_lock_to_bounds",text="Draw only within Bounds",icon="LOCKVIEW_ON")
            else:
                row2.prop(scene,"coa_lock_to_bounds",text="Draw everywhere",icon="LOCKVIEW_OFF")

### Custom template_list look
class UIListAnimationCollections(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        ob = data
        slot = item
        col = layout.row(align=True)
        if item.name not in ["NO ACTION","Restpose"]:
            col.label(icon="ACTION")
            col.prop(item,"name",emboss=False,text="")
        elif item.name == "NO ACTION":
            col.label(icon="RESTRICT_SELECT_ON")    
            col.label(text=item.name)
        elif item.name == "Restpose":
            col.label(icon="ARMATURE_DATA")    
            col.label(text=item.name)
        
                
######################################################################################################################################### Lock View
class LockView(bpy.types.Operator):
    bl_idname = "scene.coa_lock_view"
    bl_label = "Lock View"
    bl_options = {"REGISTER"}
                
    def execute(self,context):
        region_3d = context.space_data.region_3d
        bpy.data.scenes[0].coa_lock_view = True
        bpy.ops.view3d.viewnumpad(type='FRONT', align_active=False)
        if region_3d.view_perspective != "ORTHO":
            bpy.ops.view3d.view_persportho()
        set_middle_mouse_move(True)
        set_view("ORTHO",Quaternion((0.7071,0.7071,-0.0,-0.0)),True)
        return{'FINISHED'}

######################################################################################################################################### Select Child Operator
class SelectChild(bpy.types.Operator):
    bl_idname = "object.coa_select_child"
    bl_label = "select_child"
    
    ob_name = StringProperty()
    bone_name = StringProperty()
    
    def __init__(self):
        self.sprite_object = None
    
    mode = EnumProperty(items=(("object","object","object"),("bone","bone","bone")))
    def select_child(self,context):
        if self.mode == "object":
            ob = bpy.data.objects[self.ob_name]
            ob.coa_hide_select = False
            ob.coa_hide = False
            ob.select = not(ob.select)
            context.scene.objects.active = ob
                
        elif self.mode == "bone":
            armature = bpy.data.armatures[self.ob_name]
            bone = armature.bones[self.bone_name]
            bone.select = not bone.select
            bone.select_tail = not bone.select_tail
            bone.select_head = not bone.select_head
            if bone.select == True:
                armature.bones.active = bone
            else:
                armature.bones.active = None
        
    def shift_select_child(self,context):
        sprite_object = get_sprite_object(context.active_object)
        children = []
        armature = None
        if self.mode == "object":
            children = get_children(context,sprite_object,ob_list=[])
        else:
            armature = bpy.data.armatures[self.ob_name]
            for bone in  armature.bones:
                children.append(bone)
        from_index = 0
        to_index = 0
        for i,child in enumerate(children):
            if self.mode == "object":
                if child.name == self.ob_name:
                    to_index = i
            elif self.mode == "bone":
                if child.name == self.bone_name:
                    to_index = i
            if child.select == True:
                from_index = i

        select_range = []
        if from_index < to_index:
            for i in range(from_index,to_index+1):
                select_range.append(i)
        else:
            for i in range(to_index,from_index):
                select_range.append(i)  
        for i,child in enumerate(children):
            if i in select_range:
                child.coa_hide_select = False
                child.coa_hide = False
                child.select = True
                
        if self.mode == "object":
            context.scene.objects.active = bpy.data.objects[self.ob_name]
        elif self.mode == "bone":
            context.scene.objects.active = bpy.data.objects[self.ob_name]
            armature.bones.active  = armature.bones[self.bone_name]
        
    def change_weight_mode(self,context,mode):
        if self.sprite_object.coa_edit_weights:
            armature = get_armature(self.sprite_object)
            armature.select = True
            bpy.ops.object.mode_set(mode=mode)
            bpy.ops.view3d.localview()
            global tmp_active_object
            tmp_active_object = context.active_object
            
    def invoke(self,context,event):
        self.sprite_object = get_sprite_object(context.active_object)
        self.change_weight_mode(context,"OBJECT")
            
        if event.shift and not self.sprite_object.coa_edit_weights:
            self.shift_select_child(context)
        if not self.sprite_object.coa_edit_weights or ( self.sprite_object.coa_edit_weights and bpy.data.objects[self.ob_name].type == "MESH"):
            if not event.ctrl and not event.shift:
                for child in context.selected_objects:
                    child.select = False
                if self.mode == "bone":
                    for bone in bpy.data.objects[self.ob_name].data.bones:
                        bone.select = False
                        bone.select_head = False
                        bone.select_tail = False
            if not event.shift:
                self.select_child(context)
        if self.sprite_object.coa_edit_weights:     
            create_armature_parent(context)
        self.change_weight_mode(context,"WEIGHT_PAINT")
        return{'FINISHED'}
    
class CutoutAnimationCollections(bpy.types.Panel):
    bl_idname = "cutout_animation_collections"
    bl_label = "Cutout Animation Collections"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"
    bl_category = "Cutout Animation"
    
    
    def set_actions(self,context):
        scene = context.scene
        sprite_object = get_sprite_object(context.active_object)
        
        scene.frame_start = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index].frame_start
        scene.frame_end = sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index].frame_end
        set_action(context)
        for obj in context.visible_objects:
            update_uv(context,obj)
        
    bpy.types.Object.coa_anim_collections_index = IntProperty(update=set_actions)
    
    def draw(self, context):
        layout = self.layout
        obj = context.active_object
        sprite_object = get_sprite_object(obj)
        if obj != None and sprite_object != None:
            row = layout.row()
            row.template_list("UIListAnimationCollections","dummy",sprite_object, "coa_anim_collections", sprite_object, "coa_anim_collections_index",rows=1,maxrows=10,type='DEFAULT')
            col = row.column(align=True)
            col.operator("my_operator.add_animation_collection",text="",icon="ZOOMIN")
            col.operator("my_operator.remove_animation_collection",text="",icon="ZOOMOUT")
            
            
            if  len(sprite_object.coa_anim_collections) > 0 and sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index].action_collection:
                row = layout.row(align=True)
                row.label(text="Animation Length")
                row = layout.row(align=True)
                row.prop(sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index],"frame_start",text="Start")
                row.prop(sprite_object.coa_anim_collections[sprite_object.coa_anim_collections_index],"frame_end",text="End")    

preview_collections = {}