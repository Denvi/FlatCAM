Excellon Parser
===============

List of test files and their settings
-------------------------------------

========================== ============== ========= ===================
File                       Settings       Parsed Ok Example
========================== ============== ========= ===================
FlatCAM_Drilling_Test.drl  METRIC         YES       X76324 -> 76mm
Drill_All.drl              METRIC         NO        X019708 -> 1.97mm X
TFTadapter.drl             METRIC,TZ      YES?      X4.572 -> 4.57mm
rfduino dip.drl_           METRIC,TZ      NO        X236220 -> 23mm X
X-Y CONTROLLER - Drill...  METRIC         YES       X76213 -> 76mm
ucontrllerBoard.drl        INCH,TZ        YES       X1.96572
holes.drl                  INCH           YES       Y+019500 -> 1.95in
BLDC2003Through.drl        INCH           YES       X+023625 -> 2.3in
PlacaReles.drl             INCH,TZ        YES       Y-8200 -> -0.82in
AVR_Transistor_Tester.DRL  INCH           YES       X033000 -> 3.3in
DRL                        INCH,00.0000   YES/NO*   X004759 -> 0.47in
========================== ============== ========= ===================

(*) The units format is not recognized, thus it is parsed correctly
as long as the project is set for inches already.

Parser was:

.. code-block:: python

   def parse_number(self, number_str):
     if self.zeros == "L":
       match = self.leadingzeros_re.search(number_str)
       return float(number_str)/(10**(len(match.group(1)) + len(match.group(2)) - 2))
     else:  # Trailing
       return float(number_str)/10000