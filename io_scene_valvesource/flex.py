#  Copyright (c) 2013 Tom Edwards contact@steamreview.org
#
# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
from . import datamodel
from .utils import *

class DmxWriteFlexControllers(bpy.types.Operator):
	'''Generate a simple Flex Controller DMX block'''
	bl_idname = "export_scene.dmx_flex_controller"
	bl_label = "Generate DMX Flex Controller block"
	bl_options = {'UNDO','INTERNAL'}
	
	@classmethod
	def poll(self, context):
		return hasShapes(context.scene.vs.export_list[context.scene.vs.export_list_active].get_id())
	
	def execute(self, context):
		dm = datamodel.DataModel("model",1)
		
		objects = []
		shapes = []
		
		exportable = context.scene.vs.export_list[context.scene.vs.export_list_active]
		id = exportable.get_id()
		if type(id) == bpy.types.Group:
			objects.extend(list([ob for ob in id.objects if ob.data and ob.type in shape_types and ob.data.shape_keys]))
		else:
			objects.append(id)
		
		text = bpy.data.texts.new( "flex_{}".format(id.name) )
		
		root = dm.add_element(text.name,id=text.name)
		DmeCombinationOperator = dm.add_element("combinationOperator","DmeCombinationOperator",id=id.name+"controllers")
		root["combinationOperator"] = DmeCombinationOperator
		controls = DmeCombinationOperator["controls"] = datamodel.make_array([],datamodel.Element)
		
		for ob in objects:
			for shape in [shape for shape in ob.data.shape_keys.key_blocks[1:] if not "_" in shape.name]:
				DmeCombinationInputControl = dm.add_element(shape.name,"DmeCombinationInputControl",id=ob.name+shape.name+"inputcontrol")
				controls.append(DmeCombinationInputControl)
				
				DmeCombinationInputControl["rawControlNames"] = datamodel.make_array([shape.name],str)
				DmeCombinationInputControl["stereo"] = False
				DmeCombinationInputControl["eyelid"] = False
				
				DmeCombinationInputControl["flexMax"] = 1.0
				DmeCombinationInputControl["flexMin"] = 0.0
				
				DmeCombinationInputControl["wrinkleScales"] = datamodel.make_array([0.0],float)
				
		controlValues = DmeCombinationOperator["controlValues"] = datamodel.make_array( [ [0.0,0.0,0.5] ] * len(controls), datamodel.Vector3)
		DmeCombinationOperator["controlValuesLagged"] = datamodel.make_array( controlValues, datamodel.Vector3)
		DmeCombinationOperator["usesLaggedValues"] = False
		
		DmeCombinationOperator["dominators"] = datamodel.make_array([],datamodel.Element)
		targets = DmeCombinationOperator["targets"] = datamodel.make_array([],datamodel.Element)
		
		text.use_tabs_as_spaces = False
		text.from_string(dm.echo("keyvalues2",1))
		
		if not id.vs.flex_controller_source or bpy.data.texts.get(id.vs.flex_controller_source):
			id.vs.flex_controller_source = text.name
		
		self.report({'INFO'},"DMX written to text block \"{}\"".format(text.name))		
		
		return {'FINISHED'}

class ActiveDependencyShapes(bpy.types.Operator):
	'''Activates shapes found in the name of the current shape (underscore delimited)'''
	bl_idname = "object.shape_key_activate_dependents"
	bl_label = "Activate Dependency Shapes"
	bl_options = {'UNDO'}

	@classmethod
	def poll(cls, context):
		try:
			return context.active_object.active_shape_key.name.find('_') != -1
		except:
			return False

	def execute(self, context):
		context.active_object.show_only_shape_key = False
		active_key = context.active_object.active_shape_key		
		subkeys = set(active_key.name.split('_'))
		num_activated = 0
		for key in context.active_object.data.shape_keys.key_blocks:
			if key == active_key or set(key.name.split('_')) <= subkeys:
				key.value = 1
				num_activated += 1
			else:
				key.value = 0
		self.report({'INFO'},"Activated {} dependency shapes".format(num_activated - 1))
		return {'FINISHED'}

class AddCorrectiveShapeDrivers(bpy.types.Operator):
	'''Adds Blender animation drivers to corrective Source engine shapes'''
	bl_idname = "object.sourcetools_generate_corrective_drivers"
	bl_label = "Generate Corrective Shape Key Drivers"
	bl_options = {'UNDO'}

	@classmethod
	def poll(cls, context):
		return context.active_object and context.active_object.active_shape_key

	def execute(self, context):
		keys = context.active_object.data.shape_keys
		for key in keys.key_blocks:
			if key.name.find('_') != -1:
				subkeys = key.name.split('_')
				if any(keys.key_blocks.get(subkey) for subkey in subkeys):
					key.driver_remove("value")
					fcurve = key.driver_add("value")
					fcurve.modifiers.remove(fcurve.modifiers[0])
					fcurve.driver.type = 'MIN'
					for subkey in subkeys:
						if keys.key_blocks.get(subkey):
							var = fcurve.driver.variables.new()
							var.name = subkey
							var.targets[0].id_type = 'KEY'
							var.targets[0].id = keys
							var.targets[0].data_path = "key_blocks[\"{}\"].value".format(subkey)
		return {'FINISHED'}
