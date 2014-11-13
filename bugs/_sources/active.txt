Active Bugs
===================

Drill number parsing
--------------------

The screenshot below show the problematic file:

.. image:: drill_parse_problem1.png
   :align: center

The file reads::

    G81
    M48
    METRIC
    T1C00.127
    T2C00.889
    T3C00.900
    T4C01.524
    T5C01.600
    T6C02.032
    T7C02.540
    %
    T002
    X03874Y08092
    X03874Y23333
    X06414Y08092
    X06414Y23333
    X08954Y08092
    ...
    T007
    X02664Y03518
    X02664Y41618
    X76324Y03518
    X76324Y41618
    ...

After scaling by 10.0:

.. image:: drill_parse_problem2.png
   :align: center

The code involved is:

.. code-block:: python

    def __init__(self):
        ...
        self.zeros = "T"
        ...

    def parse_number(self, number_str):

        if self.zeros == "L":
            match = self.leadingzeros_re.search(number_str)
            return float(number_str)/(10**(len(match.group(2))-2+len(match.group(1))))
        else:  # Trailing
            return float(number_str)/10000

The numbers are being divided by 10000. If "L" had been specified,
the following regex would have applied:

.. code-block:: python

    # Parse coordinates
    self.leadingzeros_re = re.compile(r'^(0*)(\d*)')

Then the number 02664 would have been divided by 10**(4-2+1) = 10**3 = 1000,
which is what is desired.

Leading zeros weren't specified, but www.excellon.com says:

    The CNC-7 uses leading zeros unless you specify
    otherwise through a part program or the console.

.. note::
    The parser has been modified to default to leading
    zeros.