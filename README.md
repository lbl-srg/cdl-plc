# CDL-PLC translator

## General description

cdl-plc translates control sequences in the Control Description Language (CDL) to the IEC 61131-10 XML exchange format. The general aim of the cdl-plc translator is to transfer control sequences which were developed in the Modelica-based CDL on Programmable Logic Controllers (PLCs) standardized in IEC 61131. The IEC 61131-10 XML is an existing industry standard for the exchange of control sequences expressed in the languages according to IEC 61131-3. 

## CDL-support

The translator currently only supports control sequences including the following selected CDL blocks:
- Conversions.BooleanToInteger
- Conversions.BooleanToReal
- Logical.And
- Logical.Not
- Reals.Add
- Reals.Greater
- Reals.Hysteresis
- Reals.Limiter
- Reals.Line
- Reals.MovingAverage
- Reals.Multiply
- Reals.MultiplyByParameter
- Reals.Min
- Reals.PID
- Reals.Sources.Constant
- Reals.Subtract
- Reals.Switch.Constant

The aim of this version is to demonstrate the general feasability of the translation from CXF / `.jsonld` in the 61131-10 XML, including the creation of the XML structure, the connection of inputs / outputs or the handling of parameters. Further developments are required to cover the full scope of CDL.

## How to use the translator

1. Create a CXF representation of your CDL control sequence in `.jsonld` using the modelica-json parser.
2. Specify the path of the `.jsonld` in `cdl_plc.py` and run the script. The output will be stored in the folder `IEC61131-10XML`.
3. Import the IEC 61131-10 XML in a PLC IDE (see below for compatibility). 

## Compatibility

- The translator is compatible with CXF representations in `.jsonld` created with the modelica-json translator release 1.2.0.
- The IEC 61131-10 XML import is tested with the PLC ICE Beremiz 1.4-rc1.

## Useful links

- [Modelica-json GitHub page](https://github.com/lbl-srg/modelica-json)
- [Beremiz GitHub page](https://github.com/beremiz/beremiz)

## References

- International Electrotechnical Commission, 2019. Programmable controllers. Part 10: PLC open XML exchange format.
