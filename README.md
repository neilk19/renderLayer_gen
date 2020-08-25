# renderLayer_gen

Creates renderLayers from selected 'mesh' objects in the Maya scene -
 
 - Created renderlayer retains object reflections, shadow and lighting information
 - UI helps to keep track of created renderlayers and toggle layer visibility and rederbility
 - Qt based UI in sync and updates with changes in Maya using scriptJobs
 - Validation checks for unsupported nodes with pop up window


Installation instructions -

Paste the code below into your Maya Script editor in a Python tab and execute.
Once in your Python tab you can drag the code from there to your shelf to create a shelf button out of it.

NOTE: If you get an '_untitled_' renderlayer on using the tool that can be easily solved by going to the options in the Maya RenderLayer window
and Checking OFF "Enable untitled collections....."

import renderLayerMgr as ren
reload(ren)
