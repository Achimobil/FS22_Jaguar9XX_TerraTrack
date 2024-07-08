import bpy
import xml.etree.ElementTree as ET
import numpy as np 
from mathutils import Euler
import mathutils
import math
from math import radians

def process_object(obj_elem, materialIdToName, level=0, parent = None):
    #print(level)
    name = obj_elem.get('elementName')
    currentObject = None
    #print(obj_elem);
#    print(str(name));
    
    
    # read location from xml
    translationX = float(obj_elem.get('x'));
    translationY = float(obj_elem.get('y'));
    translationZ = float(obj_elem.get('z'));
    translationString = str(translationX) + "|" + str(translationY) + "|" + str(translationZ)
    
    # read rotation from xml and add to parent rotation
    rotationX = float(obj_elem.get('rx'));
    rotationY = float(obj_elem.get('ry'));
    rotationZ = float(obj_elem.get('rz'));
    rotationString = str(rotationX) + "|" + str(rotationY) + "|" + str(rotationZ)
        
            
    if name != None:
        
        ob = bpy.data.objects.get(name)
        obj_type = obj_elem.get('type')
                    
        if ob != None:
            if obj_type != "TRANSFORM_GROUP" and obj_type != "LIGHT_SOURCE":
                # transform groups should not be moved again, only one time added
                bpy.ops.object.select_all(action='DESELECT')
                ob.select_set(True)
#                print(name + " move to " + translationString + " with rotation " + rotationString)
                #use total position to set origin of object
                bpy.context.scene.cursor.location = (translationX,translationZ*-1,translationY)
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
                
                # for rotation. Change rotation backwards, freeze it and put forward again
                ob.rotation_euler.rotate(Euler((rotationX*-1,rotationZ,rotationY*-1), "XYZ"))
                bpy.ops.object.transform_apply(location=False, rotation=True, scale=False, properties=False, isolate_users=False)
                ob.rotation_euler.rotate(Euler((rotationX,rotationZ*-1,rotationY), "ZYX")) # use other euler type to move it the same backwards ans towards
        else:
            #print(obj_type)
            if obj_type == "TRANSFORM_GROUP":
#                print(name + " create Empty at " + translationString + " with rotation " + rotationString)
                #use total position to to create the transform group at cursor
                bpy.context.scene.cursor.location = (translationX,translationZ*-1,translationY)
                bpy.ops.object.empty_add(type='PLAIN_AXES', align='CURSOR')
                for obj in bpy.context.selected_objects:
                    obj.name = name;
                    obj.rotation_euler = (rotationX,rotationZ*-1,rotationY)
            
            if obj_type == "LIGHT_SOURCE":
#                print(name + " create Light at " + translationString + " with rotation " + rotationString)
                #use total position to to create the transform group at cursor
                bpy.ops.object.light_add(type=obj_elem.get('lightType'), location=(translationX,translationZ*-1,translationY))
                light = bpy.context.object
                light.name = name
                light.rotation_euler = (rotationX+(radians(90.0)),rotationZ,rotationY)
                light.data.energy = float(obj_elem.get('energie'))
            
    ## parents need to be set after all other stuff for the childs because of content will move otherwise
    currentObject = bpy.data.objects.get(name);
    
    # material zueisen aus liste
    materialIndex = obj_elem.get('materialIndex')
    if materialIndex != None and currentObject != None:
        mat = bpy.data.materials.get(materialIdToName[materialIndex])
        # Assign it to object
        if currentObject.data.materials:
            # assign to 1st material slot
            currentObject.data.materials[0] = mat
        else:
            # no slots
            currentObject.data.materials.append(mat)
            
    # now put the right parent to the current object
    if parent != None and currentObject != None:
        currentObject.parent = parent
        currentObject.matrix_parent_inverse = parent.matrix_world.inverted()
    
    if level < 50:
        for child_elem in obj_elem.findall('*'):
            process_object(child_elem, materialIdToName, level+1, currentObject)

            
            
def process_files(fileNode, fileIdToName):
    name = fileNode.get('filename')
    fileId = fileNode.get('fileId')
    
    #correct file patch
    if name.startswith('$data'):
        name = name.replace('$data', 'C:/Program Files (x86)/Farming Simulator 2022/data')
    if name.endswith('.png'):
        name = name.replace('.png', '.dds')
    #name = name.replace('/','\\')
    fileIdToName[fileId] = name
        
        
        
            
def process_material(materialNode, materialIdToName, fileIdToName):
    name = materialNode.get('name')
    
    # Get material
    mat = bpy.data.materials.get(name)
    if mat is None:
        # create material
        mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    
    # die anderen einstellungen scheinen komplet zu sein, schau ich später nach. erst mal zuweisen können
    materialId = materialNode.get('materialId')
    materialIdToName[materialId] = name
    
    # add shader and parameter to custom properties
    customShaderId = materialNode.get('customShaderId')
    if customShaderId != None and fileIdToName[customShaderId] != None:
        mat['customShader'] = fileIdToName[customShaderId]
        
    customShaderVariation = materialNode.get('customShaderVariation')
    if customShaderVariation != None:
        mat['customShaderVariation'] = customShaderVariation
        
    alphaBlending = materialNode.get('alphaBlending')
    if alphaBlending != None and alphaBlending == "true":
        mat.blend_method = "BLEND"
    else:
        mat.blend_method = "OPAQUE"
        
    for CustomParameter in materialNode.findall('CustomParameter'):
        mat["customParameter_" + CustomParameter.get('name')] = CustomParameter.get('value')
    
    for texture in materialNode.findall('Texture'):
        fileId = texture.get('fileId');
        #print(str(fileId));
        if fileIdToName[fileId] != None:
            #print("found")
            
            # create image texture
            image_src = bpy.data.images.load(fileIdToName[fileId], check_existing=True)
            
            mat.use_nodes = True
            #create a reference to the material output
            material_output = mat.node_tree.nodes.get('Material Output')
            Principled_BSDF = mat.node_tree.nodes.get('Principled BSDF')
            
            texImage_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texImage_node.image = image_src
            #set location of node
            material_output.location = (400, 20)
            Principled_BSDF.location = (0, 0)
            texImage_node.location = (-400, -500)
            
            link = mat.node_tree.links.new(texImage_node.outputs[0], mat.node_tree.nodes[0].inputs["Base Color"])  
    for texture in materialNode.findall('Glossmap'):
        fileId = texture.get('fileId');
        #print(str(fileId));
        if fileIdToName[fileId] != None:
            #print("found")
            
            # create image texture
            image_src = bpy.data.images.load(fileIdToName[fileId], check_existing=True)
            
            mat.use_nodes = True
            #create a reference to the material output
            material_output = mat.node_tree.nodes.get('Material Output')
            Principled_BSDF = mat.node_tree.nodes.get('Principled BSDF')
            
            texImage_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texImage_node.image = image_src
            #set location of node
            material_output.location = (400, 20)
            Principled_BSDF.location = (0, 0)
            texImage_node.location = (-400, -500)
            
            link = mat.node_tree.links.new(texImage_node.outputs[0], mat.node_tree.nodes[0].inputs["Specular"]) 
    for texture in materialNode.findall('Normalmap'):
        fileId = texture.get('fileId');
        #print(str(fileId));
        if fileIdToName[fileId] != None:
            #print("found")
            
            # create image texture
            image_src = bpy.data.images.load(fileIdToName[fileId], check_existing=True)
            
            mat.use_nodes = True
            #create a reference to the material output
            material_output = mat.node_tree.nodes.get('Material Output')
            Principled_BSDF = mat.node_tree.nodes.get('Principled BSDF')
            
            texImage_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texImage_node.image = image_src
            #set location of node
            material_output.location = (400, 20)
            Principled_BSDF.location = (0, 0)
            texImage_node.location = (-400, -500)
            
            
            normalMap_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')              
#            normalMap_node.inputs["color"]
            link = mat.node_tree.links.new(texImage_node.outputs[0], normalMap_node.inputs["Color"]) 
            
            link = mat.node_tree.links.new(normalMap_node.outputs[0], mat.node_tree.nodes[0].inputs["Normal"])                 
        

def parse_node_attributes(scene_element):
    
    name = scene_element.get('name')
    #print(name)
    object = bpy.data.objects.get(name)

    if object is not None:
        kinematic = scene_element.get('kinematic')
        if kinematic != None and kinematic == "true":
            object['I3D_kinematic'] = True
        else:
            object['I3D_kinematic'] = False
            
        static = scene_element.get('static')
        if static != None and static == "true":
            object['I3D_static'] = True
        else:
            object['I3D_static'] = False
            
        dynamic = scene_element.get('dynamic')
        if dynamic != None and dynamic == "true":
            object['I3D_dynamic'] = True
        else:
            object['I3D_dynamic'] = False
            
        compound = scene_element.get('compound')
        if compound != None and compound == "true":
            object['I3D_compound'] = True
        else:
            object['I3D_compound'] = False
            
        compoundChild = scene_element.get('compoundChild')
        if compoundChild != None and compoundChild == "true":
            object['I3D_compoundChild'] = True
        else:
            object['I3D_compoundChild'] = False
            
        collisionMask = scene_element.get('collisionMask')
        if collisionMask != None:
            object['I3D_collisionMask'] = collisionMask
        else:
            object['I3D_collisionMask'] = 255
            
        clipDistance = scene_element.get('clipDistance')
        if clipDistance != None:
            object['I3D_clipDistance'] = float(clipDistance)
        else:
            object['I3D_clipDistance'] = 0
            
        castsShadows = scene_element.get('castsShadows')
        if castsShadows != None and castsShadows == "true":
            object['I3D_castsShadows'] = True
        else:
            object['I3D_castsShadows'] = False
            
        receiveShadows = scene_element.get('receiveShadows')
        if receiveShadows != None and receiveShadows == "true":
            object['I3D_receiveShadows'] = True
        else:
            object['I3D_receiveShadows'] = False
            
        nonRenderable = scene_element.get('nonRenderable')
        if nonRenderable != None and nonRenderable == "true":
            object['I3D_nonRenderable'] = True
        else:
            object['I3D_nonRenderable'] = False
            
        trigger = scene_element.get('trigger')
        if trigger != None and trigger == "true":
            object['I3D_trigger'] = True
        else:
            object['I3D_trigger'] = False
        
            
        visibility = scene_element.get('visibility')
        if visibility != None and visibility == "false":
            object.hide_set(True)
        else:
            object.hide_set(False)
            
        
        print(object.type)
        if object.type == 'LIGHT':
            # farbe vom Licht
            color = scene_element.get('color')
            if color != None:
                colorArray = color.split()
                object.data.color.r = float(colorArray[0]);
                object.data.color.g = float(colorArray[1]);
                object.data.color.b = float(colorArray[2]);
            
            castShadowMap = scene_element.get('castShadowMap')
            if castShadowMap != None and castShadowMap == "true":
                object.data.use_shadow = True;
            else:
                object.data.use_shadow  = False
            
            range = scene_element.get('range')
            if range != None:
                object.data.cutoff_distance = float(range)
            
            coneAngle = scene_element.get('coneAngle')
            if coneAngle != None:
                object.data.spot_size = math.radians(float(coneAngle))
            
            dropOff = scene_element.get('dropOff')
            if dropOff != None :
                object.data.spot_blend = float(dropOff)/5.0
        
        
    # call recursive
    for child_elem in scene_element.findall('*'):
        parse_node_attributes(child_elem)


xml_file_path = 'D:/Achim/source/repos/FS22_Jaguar9XX_TerraTrack/sourceModel/original.i3d'
modelTree = ET.parse(xml_file_path)
modelRoot = modelTree.getroot()

print("");
print("Load file details from i3d");

fileIdToName = {}

for obj in modelRoot.findall('Files/File'):
    process_files(obj, fileIdToName)
    
print(str(fileIdToName));

print("");
print("Create Materials from i3d");

materialIdToName = {}

for obj in modelRoot.findall('Materials/Material'):
    process_material(obj, materialIdToName, fileIdToName)
    
print(str(materialIdToName));

print("");
print("Start XML correction");
# export xml benutzen
xml_file_path = 'D:/Achim/source/repos/FS22_Jaguar9XX_TerraTrack/sourceModel/exportPositions.xml'
tree = ET.parse(xml_file_path)
root = tree.getroot()
# Hauptskript: Durchlaufe alle Objekte in der Szene
for obj in root.findall('element'):
    process_object(obj, materialIdToName)


print("");
print("parse shape parameter");
for obj in modelRoot.findall('Scene/Shape'):
    parse_node_attributes(obj)

print("");
print("All done.")
