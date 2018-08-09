# -*- coding: utf-8 -*-
"""
/***************************************************************************
 clipper
                                 A QGIS plugin
 This plugin lets you use clipping function in the same shapefile selecting
  a line or polygon clips all overlaying features
                              -------------------
        begin                : 2014-06-27
        new version      : 2018-08-08 
        copyright            : (C) 2018 by Giuseppe De Marco
        email                : demarco.giuseppe@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from __future__ import absolute_import
from builtins import str
from builtins import object
from qgis.core import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtXml import *
# Initialize Qt resources from file resources.py
from . import resources_rc
#import pdb
import os.path
#import pdb
global lyr
lyr = None
class clipper(object):
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir, 'i18n', 'clipper_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        #self.dlg = clipperDialog()

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/clipper/icon.png"),
            u"Clipper", self.iface.mainWindow())
            
        self.action1 = QAction(
            QIcon(":/plugins/clipper/icon_prev_int.png"),
            u"Clipper Intersection Preview", self.iface.mainWindow())
        
        self.action2 = QAction(
            QIcon(":/plugins/clipper/icon_prev_clip.png"),
            u"Clipper Clipping Preview", self.iface.mainWindow())
            
        self.action3 = QAction(
            QIcon(":/plugins/clipper/icon_multi.png"),
            u"Clipper Clip with multiple selection", self.iface.mainWindow())
            
        #Andreas Wicht brilliant suggestion: thanks a lot for this! 
        self.action4 = QAction(
            QIcon(":/plugins/clipper/icon_paste.png"),
            u"Clipper Paste intersection", self.iface.mainWindow())
                
        #connect the action to the run method
        self.action.triggered.connect(self.run)
        self.action1.triggered.connect(self.preview_int)
        self.action2.triggered.connect(self.preview_clip)
        self.action3.triggered.connect(self.multi_clip)
        #Andreas Wicht suggestion
        self.action4.triggered.connect(self.clip_paste)
        
        # Add toolbar button and menu item the ones with icons
        self.iface.addToolBarIcon(self.action)
        self.iface.addToolBarIcon(self.action1)
        self.iface.addToolBarIcon(self.action2)
        self.iface.addToolBarIcon(self.action3)
        self.iface.addToolBarIcon(self.action4)
        
        #Add to menu action preview and clip
        self.iface.addPluginToVectorMenu(u"&Clipper", self.action)
        self.iface.addPluginToVectorMenu(u"&Clipper",  self.action1)
        self.iface.addPluginToVectorMenu(u"&Clipper", self.action2)
        self.iface.addPluginToVectorMenu(u"&Clipper", self.action3)
         #Andreas Wicht suggestion
        self.iface.addPluginToVectorMenu(u"&Clipper", self.action4)
        
    def unload(self):
        #Remove the plugin menu items and icons
        self.iface.removePluginVectorMenu(u"&Clipper", self.action)
        self.iface.removePluginVectorMenu(u"&Clipper", self.action1)
        self.iface.removePluginVectorMenu(u"&Clipper", self.action2)
        self.iface.removePluginVectorMenu(u"&Clipper", self.action3)
        #Andreas Wicht suggestion
        self.iface.removePluginVectorMenu(u"&Clipper", self.action4)
        
        self.iface.removeToolBarIcon(self.action)
        self.iface.removeToolBarIcon(self.action1)
        self.iface.removeToolBarIcon(self.action2)
        self.iface.removeToolBarIcon(self.action3)
        #Andreas Wicht suggestion
        self.iface.removeToolBarIcon(self.action4)

        
#---> Custom function begin
    def clear(self):
        if lyr:
            if lyr != None:
                layerid = lyr.id()
                if layerid:
                    if not QgsProject.instance().layerTreeRoot().findLayer(layerid).isVisible():
                        QgsProject.instance().layerTreeRoot().findLayer(layerid).setItemVisibilityChecked(True)
                        lyr.removeSelection()
        #refresh the view and clear Widgets
        self.iface.mapCanvas().refresh()
        self.iface.messageBar().clearWidgets()
        self.clear_result()
        return
    
    def clear_result(self):
        #check if there a intersect or clipped (preview) named layer in legend and remove it
        for name, layer in list(QgsProject.instance().mapLayers().items()):
            if (layer.name()== "Intersect" or layer.name() =="Clipped"):
                layid = layer.id()
                if layid:
                    QgsProject.instance().removeMapLayer(layid)
                self.iface.mapCanvas().refresh()
        return
    
    def checkvector(self):
        count = 0
        for name, layer in list(QgsProject.instance().mapLayers().items()):
            if layer.type() == QgsMapLayer.VectorLayer:
                count += 1
        return count

    def get_layer(self):
        layer = self.iface.mapCanvas().currentLayer()
        if layer:
            return layer
        else:
            self.iface.messageBar().pushMessage("Clipper"," No active layer found :please click on one!", level=Qgis.Critical, duration=3)
            
    def clip(self):
        # global variables
        global lyr #makes this variable "visibile"inside function
        lyr = None
        fsel = None
        self.clear_result()
        #close previously open messageBar
        self.iface.messageBar().popWidget()
        #clipping begin
        layer = self.get_layer()
        if layer:
            layername = layer.name()
#            provider=layer.dataProvider()
#            features = layer.getFeatures()
            for name, layer in list(QgsProject.instance().mapLayers().items()):
                if layer.type() == QgsMapLayer.VectorLayer:
                    if layer.name()== layername:
                        #--->Polygon handling
                        #check for layer type
                        if layer.wkbType() == 3 or layer.wkbType() == 6:
                            layid = layer.id()
                            #get feature selection
                            selection = layer.selectedFeatures()
                            selectids = layer.selectedFeatureIds() #modified on 2018/07/20
                            if len(selectids)!=0 and len(selectids)<2: #modified on 2018/07/20
                                box = selection[0].geometry().boundingBox()
                                request = QgsFeatureRequest(box)
                                for f in layer.getFeatures(request):
                                    #check for geometry validity...experimental
                                    if f.geometry():
                                        if f.id() == selection[0].id():
                                            fsel = f
                                    else:
                                        self.iface.messageBar().pushMessage("Clipper","possible invalid geometry id:"+str(f.id()), level=Qgis.Critical, duration=7)
                                if fsel:
                                    #set layer editable
                                    layer.startEditing()
                                    count = 0
                                    for g in layer.getFeatures(request):
                                        #check for geometry validity
                                        if g.geometry():
                                            if g.id() != fsel.id():
                                                if (g.geometry().intersects(fsel.geometry())):
                                                    #clipping non selected intersecting features
                                                    #geometry = QgsGeometry.fromPolygonXY(g.geometry().asPolygon()) #modified on 2018/07/20
                                                    attributes = g.attributes()
                                                    diff = QgsFeature()
                                                    # Calculate the difference between the original selected geometry and other features geometry only
                                                    # if the features intersects the selected geometry and set new geometry
                                                    diff.setGeometry(g.geometry().difference(fsel.geometry()))
                                                    #copy attributes from original feature
                                                    diff.setAttributes(attributes)
                                                    #add modified feature to layer
                                                    layer.addFeature(diff)
                                                    #remove old feature
                                                    if layer.deleteFeature(g.id()):
                                                        count +=1
                                                    else:
                                                        count = 0 
                                        else:
                                            self.iface.messageBar().pushMessage("Clipper","possible invalid geometry id:"+str(g.id()), level=Qgis.Critical, duration=7)
                                    #refresh the view and clear selection
                                    self.iface.mapCanvas().refresh()
                                    self.iface.mapCanvas().currentLayer().removeSelection()
                                    #restore layer visibility
                                    if not QgsProject.instance().layerTreeRoot().findLayer(layid).isVisible():
                                        QgsProject.instance().layerTreeRoot().findLayer(layid).setItemVisibilityChecked(True)
                                    if count > 1:
                                        self.iface.messageBar().pushMessage("Clipper",""+str(count)+" features clipped: "+"   Remember to save your edits...", level=Qgis.Info)
                                    else:
                                        self.iface.messageBar().pushMessage("Clipper",""+str(count)+" feature clipped: "+"   Remember to save your edits...", level=Qgis.Info)
                                else:
                                    self.iface.messageBar().pushCritical("Clipper","something wrong ... adjacent polygons?")
                            else:
                                if len(selectids)>2: #modified on 2018/07/20
                                    self.multi_clip()
                                else:
                                    self.iface.messageBar().pushMessage("Clipper"," Select at least one feature !", level=Qgis.Critical, duration=4)
                        #--->Linestring handling
                        #A bit of working is needed for LineString 2 objects or MultiLineString 5 ...
                        elif layer.wkbType() == 2 or layer.wkbType() == 5:
                            #self.iface.messageBar().pushMessage("Clipper"," Line type layer found: clip function works as a line splitter: one has to manually delete wanted clipped parts...", level=QgsMessageBar.WARNING, duration=5)
                            #get the cutting line from feature selection
                            selection = layer.selectedFeatures()
                            selectids = layer.selectedFeatureIds() #modified on 2018/07/20
                            if len(selectids) != 0:#modified on 2018/07/20
                                box =selection[0].geometry().boundingBox()
                                request = QgsFeatureRequest(box)
                                for f in layer.getFeatures(request):
                                    if f.id() == selection[0].id():
                                        fsel = f
                                    else:
                                        self.iface.messageBar().pushMessage("Clipper","possible invalid geometry id:"+str(f.id()), level=Qgis.Critical, duration=7)
                                if fsel:
                                    #unselect all features and set layer editable
                                    layer.startEditing()
                                    self.iface.mapCanvas().currentLayer().removeSelection()
                                    count = 0
                                    #select features to be splitted
                                    to_be_clipped=[]
                                    for g in layer.getFeatures(request):
                                        if g.id() != fsel.id():
                                            if (g.geometry().intersects(fsel.geometry())):
                                                to_be_clipped.append(g.id())
                                                count+=1
                                    if to_be_clipped==[]:
                                        self.iface.messageBar().pushMessage("Clipper","Clipping is not possible because no feature intersects the given line... ", level=Qgis.Critical)
                                    else:
                                        t=layer.splitFeatures(fsel.geometry().asPolyline())
                                        #refresh the view and clear selection
                                        self.iface.mapCanvas().refresh()
                                        self.iface.mapCanvas().currentLayer().removeSelection()
                                        if count > 1:
                                            self.iface.messageBar().pushMessage("Clipper",""+str(count)+" features split: "+"   Remember to save your edits...", level=Qgis.Info)
                                        else:
                                            self.iface.messageBar().pushMessage("Clipper",""+str(count)+" feature split: "+"   Remember to save your edits...", level=Qgis.Info)
                            
                            else:
                                self.iface.messageBar().pushCritical("Clipper"," Select at least one feature ! aborting ...")
#polygon intersection preview
    def preview_int(self): #Only for polygons maybe later ...
        # global variables
        global lyr #makes this variable "visibile"inside function
        lyr = None
        #remove intersect or clipped (preview) named layer in layers list 
        self.clear_result()
        #close previously open messageBar
        self.iface.messageBar().popWidget()
        #preview begin
        layer = self.get_layer()
        if layer:
            layername = layer.name()
            #provider=layer.dataProvider()
            #features = layer.getFeatures()
            for name, layer in list(QgsProject.instance().mapLayers().items()):
                if layer.type() == QgsMapLayer.VectorLayer:
                    if layer.name()== layername:
                        #--->Polygon handling
                        #check for layer type
                        if layer.wkbType() == 3 or layer.wkbType() == 6:
                            #get feature selection
                            selection = layer.selectedFeatures()
                            selectids = layer.selectedFeatureIds()#modified on 2018/07/20
                            if len(selectids)!=0:                           #modified on 2018/07/20
                                #multiple features to use as clipping stamp
                                if len(selectids) > 1:                     #modified on 2018/07/20
                                    self.iface.messageBar().pushCritical("Clipper", "Multiple selection detected intersection preview may result useless aborting...")
                                    return
                                box = selection[0].geometry().boundingBox()
                                request = QgsFeatureRequest(box)
                                for f in layer.getFeatures(request):
                                    #check for geometry validity...experimental
                                    if f.geometry():
                                        if f.id() == selection[0].id():
                                            fsel = f
                                    else:
                                        self.iface.messageBar().pushCritical("Clipper","possible invalid geometry id:"+str(f.id()))
                                if fsel:
                                    count = 0
                                    # Create a memory layer to store the result setting an initial crs
                                    #to avoid qgis from asking and check for poligon/multipolygon
                                    if layer.wkbType() == 6:
                                        resultl = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "Intersect", "memory")
                                    else:
                                        resultl = QgsVectorLayer("Polygon?crs=EPSG:4326", "Intersect", "memory")
                                    #change memorylayer crs to layer crs
                                    resultl.startEditing()
                                    resultl.setCrs(layer.crs()) 
                                    resultpr = resultl.dataProvider()
                                    #add memorylayer to canvas
                                    QgsProject.instance().addMapLayer(resultl)
                                    for g in layer.getFeatures():
                                        #check for geometry validity...experimental
                                        if g.geometry():
                                            if g.id() != fsel.id():
                                                if (g.geometry().intersects(fsel.geometry())):
                                                    #choose non selected intersecting features 
                                                    attributes = g.attributes()
                                                    inters = QgsFeature()
                                                    # Calculate the difference between the original 
                                                    # selected geometry and other features geometry only
                                                    # if the features intersects the selected geometry
                                                    #set new geometry
                                                    inters.setGeometry(g.geometry().intersection(fsel.geometry()))
                                                    #copy attributes from original feature
                                                    inters.setAttributes(attributes)
                                                    #add modified feature to memory layer
                                                    resultpr.addFeatures([inters])
                                                    count+=1
                                        else:
                                            self.iface.messageBar().pushCritical("Clipper","possible invalid geometry id:"+str(g.id()))
                                    resultl.commitChanges()
                                    #refresh the view
                                    self.iface.mapCanvas().refresh()
                                    #output messages
                                    if count > 1:
                                        widget = self.iface.messageBar().createMessage("Intersecting preview of "+str(count)+" features. To clip features click on the button:", "Clip")
                                        button = QPushButton(widget)
                                        button.setText("Clip")
                                        button.pressed.connect(self.clip)
                                        widget.layout().addWidget(button)
                                        button1 = QPushButton(widget)
                                        button1.setText("Dismiss")
                                        button1.pressed.connect(self.clear)
                                        widget.layout().addWidget(button1)
                                        self.iface.messageBar().clearWidgets()
                                        self.iface.messageBar().pushWidget(widget, Qgis.Success)
                                    else:
                                        widget = self.iface.messageBar().createMessage("Intersecting preview "+str(count)+" feature. To clip feature click on the button:", "Clip")
                                        button = QPushButton(widget)
                                        button.setText("Clip")
                                        button.pressed.connect(self.clip)
                                        widget.layout().addWidget(button)
                                        button1 = QPushButton(widget)
                                        button1.setText("Dismiss")
                                        button1.pressed.connect(self.clear)
                                        widget.layout().addWidget(button1)
                                        self.iface.messageBar().clearWidgets()
                                        self.iface.messageBar().pushWidget(widget, Qgis.Success)
                            else:
                                self.iface.messageBar().pushCritical("Clipper"," Select at least one feature !")
                        else:
                            self.iface.messageBar().pushWarning("Clipper","Unsupported type of vectorlayer: cannot perform operation, aborting...")
#polygon clipping preview
    def preview_clip(self):
        # global variables
        global lyr #makes this variable "visibile"inside function
        lyr = None
        global multisel
        multisel = 0
        if multisel == 0:
            self.clear_result()
        layer = self.get_layer()
        if layer:
            layername = layer.name()
            for name, layer in list(QgsProject.instance().mapLayers().items()):
                if layer.type() == QgsMapLayer.VectorLayer:
                    if layer.name()== layername:
                        #--->Polygon handling
                        #check for layer type 3 Polygon , 6 multipolygon
                        if layer.wkbType() == 3 or 6:
                            # get layer selected for future use
                            lyr = layer
                            #get layer's id()
                            layid = layer.id()
                            #get feature selection
                            selection = layer.selectedFeatures()
                            selectids = layer.selectedFeatureIds()                         #modified on 2018/07/20
                            if len(selectids)>0 and len(selectids)<2:                   #modified on 2018/07/20
                                multisel = 0
                                if multisel ==0:
                                    self.clear_result()
                                box = selection[0].geometry().boundingBox()
                                request = QgsFeatureRequest(box)
                                for f in layer.getFeatures(request):
                                    #check for geometry validity...experimental
                                    if f.geometry():
                                        if f.id() == selection[0].id():
                                            fsel = f
                                    else:
                                        self.iface.messageBar().pushCritical("Clipper","possible invalid geometry id:"+str(f.id()))
                                if fsel:
                                    count = 0
                                    # Create a memory layer to store the result setting an initial crs
                                    #to avoid qgis from asking
                                    resultl = QgsVectorLayer("Polygon?crs=EPSG:4326", "Clipped", "memory")
                                    #change memorylayer crs to layer crs
                                    resultl.setCrs(layer.crs()) 
                                    resultpr = resultl.dataProvider()
                                    #add memorylayer to canvas
                                    QgsProject.instance().addMapLayer(resultl)
                                    for g in layer.getFeatures():
                                        #check for geometry validity...experimental
                                        if g.geometry():
                                            if g.id() != fsel.id():
                                                if (g.geometry().intersects(fsel.geometry())):
                                                #choose non selected intersecting features
                                                    if g.geometry().wkbType() == 6:
                                                        geometry = QgsGeometry.fromMultiPolygonXY(g.geometry().asMultiPolygon())
                                                    else:    
                                                        geometry = QgsGeometry.fromPolygonXY(g.geometry().asPolygon())
                                                    attributes = g.attributes()
                                                    clipped = QgsFeature()
                                                    # Calculate the difference between the original 
                                                    # selected geometry and other features geometry only
                                                    # if the features intersects the selected geometry
                                                    #set new geometry
                                                    clipped.setGeometry(g.geometry().difference(fsel.geometry()))
                                                    #copy attributes from original feature
                                                    clipped.setAttributes(attributes)
                                                    #add modified feature to memory layer
                                                    resultpr.addFeatures([clipped])
                                                    count+=1
                                        else:
                                            self.iface.messageBar().pushMessage("Clipper","possible invalid geometry id:"+str(g.id()), level=Qgis.Critical)
                                    #refresh the view
                                    #self.iface.mapCanvas().refresh()
                                    #output messages
                                    if count > 1:
                                        #turn layer off for better clipping preview visibility
                                        QgsProject.instance().layerTreeRoot().findLayer(layid).setItemVisibilityChecked(False)
                                        #Populate messagebar
                                        widget = self.iface.messageBar().createMessage("Clipping preview of "+str(count)+" features. To clip features click on the button:", "Clip")
                                        button = QPushButton(widget)
                                        button.setText("Clip")
                                        button.pressed.connect(self.clip)
                                        widget.layout().addWidget(button)
                                        button1 = QPushButton(widget)
                                        button1.setText("Dismiss")
                                        button1.pressed.connect(self.clear)
                                        widget.layout().addWidget(button1)
                                        self.iface.messageBar().clearWidgets()
                                        self.iface.messageBar().pushWidget(widget, Qgis.Success)
                                    else:
                                        #turn layer off for better clipping preview visibility
                                        QgsProject.instance().layerTreeRoot().findLayer(layid).setItemVisibilityChecked(False)
                                        #Populate messagebar
                                        widget = self.iface.messageBar().createMessage("Clipping preview "+str(count)+" feature. To clip feature click on the button:", "Clip")
                                        button = QPushButton(widget)
                                        button.setText("Clip")
                                        button.pressed.connect(self.clip)
                                        widget.layout().addWidget(button)
                                        button1 = QPushButton(widget)
                                        button1.setText("Dismiss")
                                        button1.pressed.connect(self.clear)
                                        widget.layout().addWidget(button1)
                                        self.iface.messageBar().clearWidgets()
                                        self.iface.messageBar().pushWidget(widget, Qgis.Success)
                            else:
                                if len(selectids)>1:                                  #modified on 2018/07/20
                                    multisel = 1
                                    self.iface.messageBar().pushInfo("Clipper","Multiple selection found using multiple preview only on Multi/Polygons...")
                                    selids = layer.selectedFeatureIds()
                                    selfeat = layer.selectedFeatures()
                                    count = 0
                                    # Create a memory layer to store the result setting an initial crs
                                    #check if there's a memory layer already loaded
                                    for name, clayer in list(QgsProject.instance().mapLayers().items()):
                                        if clayer.name() == "Clipped":
                                            resultl = clayer
                                        else:
                                            resultl= None
                                    if resultl:
                                        resultpr = resultl.dataProvider()
                                    else:
                                        #to avoid qgis from asking
                                        resultl = QgsVectorLayer("Polygon?crs=EPSG:4326", "Clipped", "memory")
                                        #change memorylayer crs to layer crs
                                        resultl.setCrs(layer.crs()) 
                                        resultpr = resultl.dataProvider()
                                        #add memorylayer to canvas
                                        QgsProject.instance().addMapLayer(resultl)
                                    if selids != []:
                                        for s in selids:
                                            layer.removeSelection()
                                            layer.select(s)
                                            selection = layer.selectedFeatures()
                                            box=selection[0].geometry().boundingBox()
                                            request = QgsFeatureRequest(box)
                                            for feat in layer.getFeatures(request):
                                                if (feat.id()) == s:
                                                    for g in layer.getFeatures(request):
                                                    #check for geometry validity...experimental
                                                        if g.geometry():
                                                            if g.id() != feat.id():
                                                                if (g.geometry().intersects(feat.geometry())):
                                                                #choose non selected intersecting features
                                                                    attributes = g.attributes()
                                                                    clipped = QgsFeature()
                                                            # Calculate the difference between the original 
                                                            # selected geometry and other features geometry only
                                                            # if the features intersects the selected geometry
                                                            # set new geometry
                                                                    clipped.setGeometry(g.geometry().difference(feat.geometry()))
                                                            # copy attributes from original feature
                                                                    clipped.setAttributes(attributes)
                                                            # add modified feature to memory layer
                                                                    resultpr.addFeatures([clipped])
                                                                    count+=1
                                        layer.removeSelection()
                                        self.iface.messageBar().clearWidgets()
                                        #refresh the view
                                        self.iface.mapCanvas().refresh()
                                        #output messages
                                        if count > 1:
                                            #select features for multi_clip function
                                            lyr.select(selids)
                                            #turn layer off for better clipping preview visibility
                                            QgsProject.instance().layerTreeRoot().findLayer(layid).setItemVisibilityChecked(False)
                                            #Populate messagebar
                                            widget = self.iface.messageBar().createMessage("Preview maybe not accurate. Clipping preview of "+str(count)+" features. To clip features click on the button:", "Clip")
                                            button = QPushButton(widget)
                                            button.setText("Clip")
                                            button.pressed.connect(self.multi_clip)
                                            widget.layout().addWidget(button)
                                            button1 = QPushButton(widget)
                                            button1.setText("Dismiss")
                                            button1.pressed.connect(self.clear)
                                            widget.layout().addWidget(button1)
                                            self.iface.messageBar().clearWidgets()
                                            self.iface.messageBar().pushWidget(widget, Qgis.Success)
                                        else:
                                            #turn layer off for better clipping preview visibility
                                            QgsProject.instance().layerTreeRoot().findLayer(layid).setItemVisibilityChecked(False)
                                            #Populate messagebar
                                            widget = self.iface.messageBar().createMessage("Clipping preview "+str(count)+" feature. To clip feature click on the button:", "Clip")
                                            button = QPushButton(widget)
                                            button.setText("Clip")
                                            button.pressed.connect(self.clip)
                                            widget.layout().addWidget(button)
                                            button1 = QPushButton(widget)
                                            button1.setText("Dismiss")
                                            button1.pressed.connect(self.clear)
                                            widget.layout().addWidget(button1)
                                            self.iface.messageBar().clearWidgets()
                                            self.iface.messageBar().pushWidget(widget, Qgis.Success)
                                else:
                                    self.iface.messageBar().pushMessage("Clipper"," Select at least one feature !", level=Qgis.Critical, duration=4)
    
    def multi_clip(self): #only for polygons
        global lyr
        if lyr != None:
            layer =lyr
        else:
            layer = self.get_layer()
        if layer:
            layername = layer.name()
            for name, layer in list(QgsProject.instance().mapLayers().items()):
                if layer.type() == QgsMapLayer.VectorLayer:
                    if layer.name()== layername:
                        #--->Polygon handling
                        #check for layer type 3 Polygon , 6 multipolygon
                        if layer.wkbType() == 3 or 6:
                            # get layer selected for future use
                            lyr = layer
                            #get layer selection ids
                            selectids = layer.selectedFeatureIds()
                            if len(selectids)>1 :
                                for n in selectids:
                                    layer.removeSelection()
                                    layer.select(n)
                                    self.clip()
                            else:
                                self.iface.messageBar().pushCritical("Clipper"," No multiple selection found , aborting ...")

#polygon intersection clip & paste: an Andreas Wicht suggestion implemented july 18th 2018 by G. De Marco
    def clip_paste(self):
        #Find intersection------------------------------------------------------------------------------------------------------------------------
        # global variables
        global lyr #makes this variable "visibile"inside function
        lyr = None
        #remove intersect or clipped (preview) named layer in layers list 
        self.clear_result()
        #close previously open messageBar
        self.iface.messageBar().popWidget()
        #preview begin
        layer = self.get_layer()
        if layer:
            layername = layer.name()
            for name, layer in list(QgsProject.instance().mapLayers().items()):
                if layer.type() == QgsMapLayer.VectorLayer:
                    if layer.name()== layername:
                        #--->Polygon handling
                        #check for layer type
                        if layer.wkbType() == 3 or layer.wkbType() == 6:
                            #get feature selection
                            selection = layer.selectedFeatures()
                            selectids = layer.selectedFeatureIds()#modified on 2018/07/20
                            if len(selectids)!=0:                           #modified on 2018/07/20
                                #multiple features to use as clipping stamp
                                if len(selectids) > 1:                     #modified on 2018/07/20
                                    self.iface.messageBar().pushCritical("Clipper", "Multiple selection detected intersection preview may result useless aborting...")
                                    return
                                box = selection[0].geometry().boundingBox()
                                request = QgsFeatureRequest(box)
                                for f in layer.getFeatures(request):
                                    #check for geometry validity
                                    if f.geometry():
                                        if f.id() == selection[0].id():
                                            fsel = f
                                    else:
                                        self.iface.messageBar().pushCritical("Clipper","possible invalid geometry id:"+str(f.id()))
                                if fsel:
                                    count = 0
                                    # Create a memory layer to store the result setting an initial crs
                                    #to avoid qgis from asking and check for poligon/multipolygon
                                    if layer.wkbType() == 6:
                                        resultl = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "Intersect", "memory")
                                    else:
                                        resultl = QgsVectorLayer("Polygon?crs=EPSG:4326", "Intersect", "memory")
                                    #change memorylayer crs to layer crs
                                    resultl.startEditing()
                                    resultl.setCrs(layer.crs()) 
                                    resultpr = resultl.dataProvider()
                                    for g in layer.getFeatures():
                                        #check for geometry validity.
                                        if g.geometry():
                                            if g.id() != fsel.id():
                                                if (g.geometry().intersects(fsel.geometry())):
                                                    #choose non selected intersecting features 
                                                    attributes = g.attributes()
                                                    inters = QgsFeature()
                                                    # Calculate the difference between the original 
                                                    # selected geometry and other features geometry only
                                                    # if the features intersects the selected geometry
                                                    #set new geometry
                                                    inters.setGeometry(g.geometry().intersection(fsel.geometry()))
                                                    #copy attributes from original feature
                                                    inters.setAttributes(attributes)
                                                    #add modified feature to memory layer
                                                    resultpr.addFeatures([inters])
                                                    count+=1
                                        else:
                                            self.iface.messageBar().pushCritical("Clipper","possible invalid geometry id:"+str(g.id()))
                                    #save memory layer
                                    resultl.commitChanges()
                                    #refresh the view
                                    self.iface.mapCanvas().refresh()
#----------------finished intersection creation, now it's time to move on:
#--------------- c'mon baby .... let's do the clip .... 
#                                    pyqtRemoveInputHook()
#                                    pdb.set_trace()
                                    if count >0:
                                        cnt = 0
                                        #clear selection
                                        layer.removeSelection()
                                        #refresh the view
                                        self.iface.mapCanvas().refresh()
                                        layer.startEditing()
                                        #paste intersecting features from memory layer select and clip
                                        for p in resultl.getFeatures():
                                            if p.geometry():
                                                #request features with boundingbox 
                                                resultl.select(p.id())
                                                selection = resultl.selectedFeatures()
                                                rbox = selection[0].geometry().boundingBox()
                                                rrequest = QgsFeatureRequest(rbox)
                                                for z in layer.getFeatures(rrequest):
                                                    if (z.geometry().intersects(p.geometry())):
                                                        attributes = z.attributes()
                                                        diff = QgsFeature()
                                                    # Calculate the difference between the original selected geometry and other features geometry only
                                                    # if the features intersects the selected geometry and set new geometry
                                                        diff.setGeometry(z.geometry().difference(p.geometry()))
                                                    #copy attributes from original feature
                                                        diff.setAttributes(attributes)
                                                    #add modified feature to layer
                                                        layer.addFeature(diff)
                                                    #remove old feature
                                                        if layer.deleteFeature(z.id()):
                                                            clipcount +=1
                                                        else:
                                                            clipcount = 0 
                                                #assign values to feature to be pasted
                                                geom = p.geometry()
                                                attrs = p.attributes()
                                                pastef = QgsFeature()
                                                pastef.setGeometry(geom)
                                                #set an id not to lose the pasted feature reference...
#                                                id = 9999+cnt
#                                                pastef.setId(id)
                                                #copy attributes from original feature
                                                pastef.setAttributes(attrs)                                  
                                                #add modified feature to memory layer
                                                if layer.dataProvider().addFeatures([pastef]):
                                                    cnt +=1
                                            else:
                                                self.iface.messageBar().pushCritical("Clipper","possible invalid geometry id:"+str(p.id()))
                                        if cnt >0:
                                            widget = self.iface.messageBar().createMessage("Clip and Paste of "+str(cnt)+" Intersecting features successful.Remember to manually save your edits if the outcome is satisfactory ...", " Clipper")
                                            button = QPushButton(widget)
                                            button.setText("Dismiss")
                                            button.pressed.connect(self.clear)
                                            widget.layout().addWidget(button)
                                            self.iface.messageBar().clearWidgets()
                                            self.iface.messageBar().pushWidget(widget, Qgis.Success)
                                        else:
                                            self.iface.messageBar().pushCritical("Clipper","No intersecting features") 
                                    else:
                                        self.iface.messageBar().pushCritical("Clipper","No intersecting features") 
                            else:
                                self.iface.messageBar().pushCritical("Clipper", "No selected feature aborting...")
                                return
#---> Custom functions end 
    # run method that performs all the real work
    def run(self):
        self.clear_result()
        check = 0
        check = self.checkvector()
        if check == 0:
            self.iface.messageBar().pushCritical("Clipper"," No Vector layer found !")
            pass
        else:
            self.clip()
