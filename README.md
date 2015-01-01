FlatCAM: 2D Post-processing for Manufacturing
=============================================

(c) 2014 Juan Pablo Caram

FlatCAM is a program for preparing CNC jobs for making PCBs on a CNC router.
Among other things, it can take a Gerber file generated by your favorite PCB
CAD program, and create G-Code for Isolation routing. But there's more.





This  fork is  mainly for improving shell  commands.

added so far:

* cutout
* mirror
* cncdrilljob


todo:

* commandline  witch  reads  whole shell sequence from given file


example of  shell flow:

```
#!flatcam shell


new 
open_gerber /home/sopak/kicad/ThermalShield/Gerber/ThermalPicoShield2-Margin.gbr  -outname Margin
open_gerber /home/sopak/kicad/ThermalShield/Gerber/ThermalPicoShield2-B_Cu.gbr  -outname BottomCu
open_excellon /home/sopak/kicad/ThermalShield/Gerber/ThermalPicoShield2.drl -outname Drills

mirror BottomCu -box Margin -axis X

mirror Drills -box Margin -axis X

cutout Margin -dia 3 -margin 0 -gapsize 0.6 -gaps lr

isolate BottomCu -dia 0.4 -overlap 1

drillcncjob Drills -tools 1 -drillz -2 -travelz 2 -feedrate 5 -outname Drills_cncjob_0.8

drillcncjob Drills -tools 2 -drillz -2 -travelz 2 -feedrate 5 -outname Drills_cncjob_3.0

cncjob BottomCu_iso -tooldia 0.4

cncjob Margin_cutout -tooldia 3

write_gcode BottomCu_iso_cnc /home/sopak/kicad/ThermalShield/Gerber/ThermalPicoShield2-B_Cu.gbr_iso_cnc.ngc

write_gcode Margin_cutout_cnc /home/sopak/kicad/ThermalShield/Gerber/ThermalPicoShield2-Margin.gbr_cutout_cnc.ngc

write_gcode Drills_cncjob_3.0 /home/sopak/kicad/ThermalShield/Gerber/ThermalPicoShield2.drl_Drills_cncjob_3.0.ngc

write_gcode Drills_cncjob_0.8 /home/sopak/kicad/ThermalShield/Gerber/ThermalPicoShield2.drl_Drills_cncjob_0.8.ngc
```
